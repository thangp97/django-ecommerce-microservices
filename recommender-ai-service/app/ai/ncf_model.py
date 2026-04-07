"""
NCF - Neural Collaborative Filtering
=====================================
Đây là mô hình Deep Learning dự đoán sản phẩm phù hợp với từng khách hàng.

Kiến trúc NCF gồm 2 nhánh:
  1. GMF (Generalized Matrix Factorization):
     - Học tương tác TUYẾN TÍNH giữa user và item
     - Dùng phép nhân element-wise của 2 embedding vectors

  2. MLP (Multi-Layer Perceptron):
     - Học tương tác PHI TUYẾN TÍNH (phức tạp hơn)
     - Nối 2 embedding vectors → đưa qua các lớp Neural Network

  Kết quả cuối = kết hợp output của GMF + MLP → sigmoid → xác suất tương tác

Tham khảo: "Neural Collaborative Filtering" - He et al., 2017
"""

import os
import json
import torch
import torch.nn as nn
import numpy as np

MODEL_DIR = os.environ.get('AI_MODEL_DIR', '/app/ai_models')
MODEL_PATH = os.path.join(MODEL_DIR, 'ncf_model.pt')
META_PATH = os.path.join(MODEL_DIR, 'ncf_meta.json')


class NCFModel(nn.Module):
    """
    Neural Collaborative Filtering Model.

    Embedding: Biến user_id/item_id (số nguyên) thành vector số thực.
    Ví dụ: user_id=5 → [0.23, -0.51, 0.87, ...] (embedding_dim chiều)

    Các user/item "tương tự nhau" sẽ có embedding vectors gần nhau trong không gian vector.
    """

    def __init__(self, num_users, num_items, embedding_dim=32):
        super().__init__()

        # === Nhánh GMF ===
        # Học ma trận tương tác tuyến tính (giống Matrix Factorization truyền thống)
        self.user_emb_gmf = nn.Embedding(num_users + 1, embedding_dim)
        self.item_emb_gmf = nn.Embedding(num_items + 1, embedding_dim)

        # === Nhánh MLP ===
        # Học tương tác phi tuyến tính qua các lớp neural network
        self.user_emb_mlp = nn.Embedding(num_users + 1, embedding_dim)
        self.item_emb_mlp = nn.Embedding(num_items + 1, embedding_dim)

        # Các lớp MLP: input(64) → hidden(32) → hidden(16)
        self.mlp = nn.Sequential(
            nn.Linear(embedding_dim * 2, 64),
            nn.ReLU(),           # Hàm kích hoạt phi tuyến
            nn.Dropout(0.2),     # Dropout: ngẫu nhiên tắt 20% neurons → chống overfitting
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, 16),
            nn.ReLU(),
        )

        # Lớp output cuối: kết hợp GMF (32 chiều) + MLP output (16 chiều) → 1 điểm
        self.predict_layer = nn.Linear(embedding_dim + 16, 1)
        self.sigmoid = nn.Sigmoid()  # Sigmoid: ép kết quả về [0, 1] = xác suất

        # Khởi tạo trọng số (Xavier initialization giúp training ổn định hơn)
        self._init_weights()

    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, std=0.01)
            elif isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(self, user_ids, item_ids):
        """
        Forward pass: tính xác suất user tương tác với item.

        Args:
            user_ids: tensor chứa user indices [batch_size]
            item_ids: tensor chứa item indices [batch_size]

        Returns:
            tensor xác suất [batch_size] trong khoảng [0, 1]
        """
        # === GMF branch ===
        user_gmf = self.user_emb_gmf(user_ids)   # [batch, embedding_dim]
        item_gmf = self.item_emb_gmf(item_ids)   # [batch, embedding_dim]
        gmf_out = user_gmf * item_gmf            # element-wise product [batch, embedding_dim]

        # === MLP branch ===
        user_mlp = self.user_emb_mlp(user_ids)   # [batch, embedding_dim]
        item_mlp = self.item_emb_mlp(item_ids)   # [batch, embedding_dim]
        mlp_input = torch.cat([user_mlp, item_mlp], dim=1)  # nối vector: [batch, embedding_dim*2]
        mlp_out = self.mlp(mlp_input)             # [batch, 16]

        # === Kết hợp GMF + MLP ===
        combined = torch.cat([gmf_out, mlp_out], dim=1)  # [batch, embedding_dim+16]
        output = self.sigmoid(self.predict_layer(combined))
        return output.squeeze()


class NCFTrainer:
    """
    Quản lý việc train, lưu và load mô hình NCF.
    """

    def __init__(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        self.model = None
        self.user_map = {}   # customer_id → index trong embedding
        self.item_map = {}   # product_id → index trong embedding
        self.item_info = {}  # lưu thông tin sản phẩm để trả về kết quả

    def prepare_data(self, interactions):
        """
        Chuẩn bị dữ liệu training từ danh sách tương tác.

        interactions: list of dict {"user_id": int, "item_id": str, "rating": float}

        "item_id" dùng string vì ta gộp sách ("book_1") và quần áo ("clothe_2")
        vào cùng một không gian item.
        """
        # Tạo mapping từ ID thực → index (0, 1, 2, ...)
        # Vì Embedding layer cần index liên tục, không phải ID bất kỳ
        users = sorted(set(d['user_id'] for d in interactions))
        items = sorted(set(d['item_id'] for d in interactions))

        self.user_map = {uid: idx for idx, uid in enumerate(users)}
        self.item_map = {iid: idx for idx, iid in enumerate(items)}

        # Tạo tập positive samples (user thực sự đã mua/đánh giá cao)
        positives = set()
        for d in interactions:
            if d['rating'] >= 3.0:  # rating >= 3 coi là tích cực
                positives.add((d['user_id'], d['item_id']))

        # Tạo training data: positive + negative sampling
        # Negative sampling: với mỗi positive, tạo N negative (user KHÔNG tương tác với item đó)
        train_users, train_items, train_labels = [], [], []

        for user_id, item_id in positives:
            # Thêm positive sample (label = 1)
            train_users.append(self.user_map[user_id])
            train_items.append(self.item_map[item_id])
            train_labels.append(1.0)

            # Thêm 4 negative samples (label = 0)
            neg_count = 0
            all_items = list(self.item_map.keys())
            np.random.shuffle(all_items)
            for neg_item in all_items:
                if (user_id, neg_item) not in positives:
                    train_users.append(self.user_map[user_id])
                    train_items.append(self.item_map[neg_item])
                    train_labels.append(0.0)
                    neg_count += 1
                    if neg_count >= 4:
                        break

        return (
            torch.LongTensor(train_users),
            torch.LongTensor(train_items),
            torch.FloatTensor(train_labels),
        )

    def train(self, interactions, item_info, epochs=20, lr=0.001, batch_size=256):
        """
        Train mô hình NCF.

        Args:
            interactions: lịch sử tương tác user-item
            item_info: dict thông tin sản phẩm để lưu meta
            epochs: số lần duyệt qua toàn bộ data
            lr: learning rate - tốc độ học (nhỏ → học chậm nhưng ổn định)
            batch_size: số samples xử lý một lần
        """
        if len(interactions) < 5:
            return {"error": "Cần ít nhất 5 lượt tương tác để train mô hình"}

        self.item_info = item_info
        user_tensor, item_tensor, label_tensor = self.prepare_data(interactions)

        num_users = len(self.user_map)
        num_items = len(self.item_map)

        self.model = NCFModel(num_users, num_items, embedding_dim=32)
        # BCELoss: Binary Cross Entropy Loss - phù hợp bài toán phân loại nhị phân (mua/không mua)
        criterion = nn.BCELoss()
        # Adam optimizer: adaptive learning rate, hội tụ nhanh hơn SGD thông thường
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)

        self.model.train()
        dataset_size = len(label_tensor)
        history = []

        for epoch in range(epochs):
            # Xáo trộn data mỗi epoch để tránh bias thứ tự
            perm = torch.randperm(dataset_size)
            epoch_loss = 0.0
            num_batches = 0

            for i in range(0, dataset_size, batch_size):
                batch_idx = perm[i:i + batch_size]
                batch_users = user_tensor[batch_idx]
                batch_items = item_tensor[batch_idx]
                batch_labels = label_tensor[batch_idx]

                # Forward pass: tính dự đoán
                predictions = self.model(batch_users, batch_items)
                loss = criterion(predictions, batch_labels)

                # Backward pass: tính gradient và cập nhật trọng số
                optimizer.zero_grad()  # Xóa gradient cũ
                loss.backward()        # Tính gradient (chain rule)
                optimizer.step()       # Cập nhật weights: w = w - lr * gradient

                epoch_loss += loss.item()
                num_batches += 1

            avg_loss = epoch_loss / num_batches
            history.append(avg_loss)

            if (epoch + 1) % 5 == 0:
                print(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f}")

        # Lưu model và metadata
        self._save(num_users, num_items)
        return {
            "status": "success",
            "epochs": epochs,
            "final_loss": history[-1],
            "num_users": num_users,
            "num_items": num_items,
            "num_interactions": len(interactions),
        }

    def _save(self, num_users, num_items):
        """Lưu model weights và metadata ra file."""
        torch.save(self.model.state_dict(), MODEL_PATH)
        meta = {
            "num_users": num_users,
            "num_items": num_items,
            "user_map": {str(k): v for k, v in self.user_map.items()},
            "item_map": {str(k): v for k, v in self.item_map.items()},
            "item_info": self.item_info,
        }
        with open(META_PATH, 'w') as f:
            json.dump(meta, f)

    def load(self):
        """Load model đã train từ file."""
        if not os.path.exists(MODEL_PATH) or not os.path.exists(META_PATH):
            return False
        with open(META_PATH, 'r') as f:
            meta = json.load(f)

        self.user_map = {int(k): v for k, v in meta['user_map'].items()}
        self.item_map = meta['item_map']
        self.item_info = meta.get('item_info', {})

        self.model = NCFModel(meta['num_users'], meta['num_items'], embedding_dim=32)
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
        self.model.eval()
        return True

    def recommend(self, customer_id, top_k=5, exclude_ids=None):
        """
        Dự đoán top_k sản phẩm phù hợp nhất cho customer_id.

        Cách hoạt động:
        1. Lấy user embedding của customer_id
        2. Tính xác suất tương tác với TẤT CẢ items
        3. Sắp xếp giảm dần → lấy top_k
        """
        if self.model is None:
            loaded = self.load()
            if not loaded:
                return None, "Model chưa được train"

        if customer_id not in self.user_map:
            return None, "Khách hàng chưa có đủ lịch sử mua hàng để dùng AI model"

        exclude_ids = set(exclude_ids or [])
        user_idx = self.user_map[customer_id]

        # Tạo tensor chứa user_idx lặp lại cho tất cả items
        all_item_keys = list(self.item_map.keys())
        user_tensor = torch.LongTensor([user_idx] * len(all_item_keys))
        item_tensor = torch.LongTensor([self.item_map[k] for k in all_item_keys])

        with torch.no_grad():  # Không cần tính gradient khi inference
            scores = self.model(user_tensor, item_tensor).numpy()

        # Sắp xếp theo score giảm dần
        sorted_indices = np.argsort(scores)[::-1]

        results = []
        for idx in sorted_indices:
            item_key = all_item_keys[idx]
            if item_key in exclude_ids:
                continue
            item_data = self.item_info.get(item_key, {"id": item_key})
            item_data['ai_score'] = float(scores[idx])
            results.append(item_data)
            if len(results) >= top_k:
                break

        return results, None


# Singleton instance - dùng chung trong toàn service
ncf_trainer = NCFTrainer()
