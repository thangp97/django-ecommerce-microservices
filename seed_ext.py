"""Seed 10 product-service mới (>=10 sản phẩm/loại) + 500 users.

Chạy: python seed_ext.py
Yêu cầu: docker compose up xong, các service đã healthy.
"""
import io
import random
import sys
import time

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

random.seed(42)

CUSTOMER_URL = 'http://localhost:8001'

# (host_port, plural, product_list)
SERVICES = [
    (8020, 'electronics', 'electronic'),
    (8021, 'foods',       'food'),
    (8022, 'toys',        'toy'),
    (8023, 'furnitures',  'furniture'),
    (8024, 'cosmetics',   'cosmetic'),
    (8025, 'sports',      'sport'),
    (8026, 'stationeries', 'stationery'),
    (8027, 'appliances',  'appliance'),
    (8028, 'jewelries',   'jewelry'),
    (8029, 'pet-supplies', 'pet-supply'),
]


def ok(msg): print(f'  [OK]   {msg}')
def err(msg): print(f'  [ERR]  {msg}')
def info(msg): print(f'  [-->]  {msg}')
def section(msg): print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def post(url, data):
    try:
        r = requests.post(url, json=data, timeout=10)
        return r.json() if r.text else {}, r.status_code
    except Exception as e:
        return {'error': str(e)}, 0


# ────────────────────────────────────────────────────────
# PRODUCT DATA
# ────────────────────────────────────────────────────────

PRODUCT_DATA = {
    'electronic': [
        # name, price, stock, desc, category, brand, warranty_months, power_w
        ('iPhone 15 Pro Max 256GB', 32990000, 25, 'Điện thoại cao cấp chip A17 Pro, camera 48MP', 'Điện thoại', 'Apple', 12, 20),
        ('Samsung Galaxy S24 Ultra', 29990000, 30, 'Flagship Android màn Dynamic AMOLED 6.8"', 'Điện thoại', 'Samsung', 12, 25),
        ('Laptop Dell XPS 15', 42000000, 12, 'Intel Core i9 RAM 32GB SSD 1TB OLED 4K', 'Laptop', 'Dell', 24, 90),
        ('MacBook Air M3 13"', 28990000, 18, 'Chip M3 8-core, pin 18 giờ, mỏng nhẹ', 'Laptop', 'Apple', 12, 30),
        ('Tai nghe Sony WH-1000XM5', 7990000, 40, 'Noise cancelling hàng đầu, pin 30 giờ', 'Âm thanh', 'Sony', 12, 5),
        ('AirPods Pro 2', 6490000, 50, 'Chống ồn chủ động, Spatial Audio', 'Âm thanh', 'Apple', 12, 2),
        ('Smart TV LG OLED 55"', 35990000, 8, 'OLED evo 4K 120Hz, webOS 23', 'TV', 'LG', 24, 180),
        ('Máy ảnh Canon EOS R6', 58990000, 6, 'Full-frame mirrorless 20MP, quay 4K/60', 'Máy ảnh', 'Canon', 24, 10),
        ('iPad Air M2 11"', 17990000, 22, 'Chip M2, màn Liquid Retina, bút Pencil Pro', 'Máy tính bảng', 'Apple', 12, 12),
        ('Đồng hồ Apple Watch Series 9', 10990000, 35, 'Theo dõi sức khỏe, GPS, chống nước 50m', 'Đồng hồ', 'Apple', 12, 1),
        ('Chuột Logitech MX Master 3S', 2490000, 60, 'Chuột không dây ergonomic, 8K DPI', 'Phụ kiện', 'Logitech', 24, 1),
        ('Bàn phím cơ Keychron Q1', 4290000, 25, 'Hot-swap, aluminum, RGB per-key', 'Phụ kiện', 'Keychron', 12, 2),
    ],
    'food': [
        # name, price, stock, desc, category, origin, weight_g, expiry_date
        ('Cà phê Trung Nguyên Legend', 185000, 120, 'Cà phê pha phin đậm đà vị Việt', 'Cà phê', 'Việt Nam', 500, '2026-12-31'),
        ('Trà Olong Tâm Châu', 220000, 80, 'Trà cao cấp vùng Bảo Lộc', 'Trà', 'Việt Nam', 200, '2027-06-30'),
        ('Hạt điều rang muối Bình Phước', 165000, 150, 'Hạt điều W240 loại 1, rang mộc', 'Hạt khô', 'Việt Nam', 500, '2026-10-15'),
        ('Socola Lindt Excellence 70%', 95000, 200, 'Socola đen Thụy Sĩ 70% cacao', 'Bánh kẹo', 'Thụy Sĩ', 100, '2026-08-20'),
        ('Mật ong rừng U Minh', 285000, 60, 'Mật ong nguyên chất, hoa rừng ngập mặn', 'Mật ong', 'Việt Nam', 1000, '2028-01-01'),
        ('Bánh trung thu Kinh Đô', 68000, 300, 'Nhân thập cẩm trứng muối truyền thống', 'Bánh kẹo', 'Việt Nam', 150, '2026-09-15'),
        ('Mì tôm Omachi', 28000, 500, 'Hộp 5 gói mì ly sườn hầm ngũ quả', 'Mì ăn liền', 'Việt Nam', 400, '2026-11-30'),
        ('Sữa TH True Milk 1L', 35000, 400, 'Sữa tươi tiệt trùng không đường', 'Sữa', 'Việt Nam', 1000, '2026-05-20'),
        ('Gạo ST25 5kg', 280000, 180, 'Gạo ngon nhất thế giới 2019', 'Gạo', 'Việt Nam', 5000, '2026-12-31'),
        ('Dầu ăn Simply 1L', 58000, 220, 'Dầu đậu nành, không cholesterol', 'Gia vị', 'Việt Nam', 1000, '2027-03-15'),
        ('Kẹo dẻo Haribo Goldbears', 85000, 250, 'Kẹo dẻo gấu vàng nổi tiếng Đức', 'Bánh kẹo', 'Đức', 200, '2026-07-10'),
    ],
    'toy': [
        # name, price, stock, desc, category, age_range, material
        ('LEGO Classic 11017', 890000, 45, 'Bộ xếp hình sáng tạo 484 mảnh', 'Xếp hình', '4+', 'Nhựa ABS'),
        ('Búp bê Barbie Dreamhouse', 1290000, 30, 'Nhà búp bê 3 tầng cao cấp', 'Búp bê', '3+', 'Nhựa'),
        ('Xe điều khiển RC Buggy', 650000, 60, 'Xe đua off-road 4WD pin sạc', 'Xe', '6+', 'Nhựa + kim loại'),
        ('Bộ xếp Rubik 3x3 GAN', 450000, 80, 'Rubik thi đấu magnetic speedcube', 'Giải đố', '8+', 'Nhựa'),
        ('Gấu bông Teddy 80cm', 380000, 120, 'Gấu bông siêu mềm, quà tặng', 'Thú bông', '0+', 'Vải bông'),
        ('Đường ray tàu hỏa gỗ', 720000, 40, 'Set tàu gỗ 80 mảnh tương thích Brio', 'Xe', '3+', 'Gỗ tự nhiên'),
        ('Slime kit 10 màu', 185000, 150, 'Bộ đồ chơi làm slime sáng tạo', 'Thủ công', '6+', 'Hóa chất an toàn'),
        ('Đồ chơi nấu ăn IKEA', 520000, 70, 'Bộ bếp mini 10 món', 'Nhập vai', '3+', 'Gỗ + nhựa'),
        ('Lắp ráp Magnetic 100 mảnh', 580000, 55, 'Nam châm từ tính phát triển trí não', 'Xếp hình', '3+', 'Nhựa + nam châm'),
        ('Búa đập chuột Whack-a-Mole', 320000, 90, 'Đồ chơi đập chuột có âm thanh', 'Điện tử', '3+', 'Nhựa'),
        ('Play-Doh 10 hộp', 280000, 180, 'Đất nặn siêu mềm 10 màu', 'Thủ công', '2+', 'Bột an toàn'),
    ],
    'furniture': [
        # name, price, stock, desc, category, dimensions, material, color
        ('Ghế công thái học Sihoo M57', 3290000, 20, 'Tựa lưới, tựa đầu, kê chân tùy chỉnh', 'Ghế', '65x65x115cm', 'Lưới + kim loại', 'Đen'),
        ('Bàn làm việc Ergonomic L-shape', 4890000, 15, 'Bàn chữ L 160cm, chống mỏi lưng', 'Bàn', '160x120x75cm', 'Gỗ MDF + thép', 'Nâu'),
        ('Sofa 3 chỗ da bò', 18900000, 8, 'Sofa da thật, khung gỗ tự nhiên', 'Sofa', '220x90x85cm', 'Da bò', 'Xám'),
        ('Giường ngủ 1m6 gỗ sồi', 8500000, 12, 'Giường đôi có ngăn chứa đồ', 'Giường', '200x160x45cm', 'Gỗ sồi', 'Nâu gỗ'),
        ('Tủ quần áo 4 cánh', 6290000, 18, 'Tủ quần áo nhiều ngăn, có gương', 'Tủ', '200x200x60cm', 'MDF phủ Melamine', 'Trắng'),
        ('Bàn ăn 6 chỗ gỗ cao su', 5890000, 14, 'Bộ bàn ăn kèm 6 ghế', 'Bàn', '160x90x75cm', 'Gỗ cao su', 'Nâu'),
        ('Kệ sách 5 tầng gỗ công nghiệp', 1290000, 35, 'Kệ decor đa năng', 'Kệ', '80x30x180cm', 'MDF', 'Đen'),
        ('Đèn sàn Bắc Âu', 890000, 50, 'Đèn đứng chân gỗ, chóa vải', 'Đèn', '160cm', 'Gỗ + vải', 'Trắng ngà'),
        ('Thảm trải sàn Ba Tư', 2490000, 25, 'Thảm họa tiết cổ điển 1.6x2.3m', 'Thảm', '160x230cm', 'Sợi polyester', 'Đỏ'),
        ('Bàn trà sofa mặt kính', 1890000, 22, 'Bàn trà hiện đại, khung kim loại', 'Bàn', '120x60x45cm', 'Kính cường lực + thép', 'Đen'),
        ('Tủ giày 5 tầng thông minh', 1590000, 40, 'Tủ giày lật, tiết kiệm không gian', 'Tủ', '80x24x180cm', 'MDF', 'Trắng'),
    ],
    'cosmetic': [
        # name, price, stock, desc, category, skin_type, volume_ml, expiry
        ('Kem chống nắng Anessa Gold', 650000, 80, 'Sunscreen SPF50+ PA++++ chịu nước', 'Chống nắng', 'Mọi loại da', 60, '2027-06-30'),
        ('Son YSL Rouge Pur Couture', 1150000, 40, 'Son thỏi lì cao cấp Pháp', 'Trang điểm', 'Mọi loại da', 4, '2028-01-01'),
        ('Nước hoa hồng Klairs Toner', 450000, 120, 'Toner không cồn dịu nhẹ', 'Skincare', 'Da nhạy cảm', 180, '2027-03-15'),
        ('Serum Vitamin C La Roche', 890000, 60, 'Serum sáng da Pure Vitamin C 10', 'Serum', 'Da thường', 30, '2027-09-20'),
        ('Sữa rửa mặt Cetaphil Gentle', 325000, 200, 'Sữa rửa mặt dịu nhẹ cho da nhạy cảm', 'Làm sạch', 'Da nhạy cảm', 500, '2027-11-15'),
        ('Kem dưỡng Estée Lauder Night Repair', 2490000, 25, 'Serum đêm phục hồi tái tạo da', 'Dưỡng đêm', 'Da trưởng thành', 50, '2027-08-10'),
        ('Mặt nạ SK-II Facial Treatment', 1290000, 35, 'Mặt nạ dưỡng trắng essence', 'Mặt nạ', 'Mọi loại da', 150, '2027-05-20'),
        ('Phấn phủ Innisfree No Sebum', 185000, 150, 'Phấn phủ kiềm dầu kiềm bóng', 'Trang điểm', 'Da dầu', 5, '2027-12-31'),
        ('Tẩy trang Bioderma Sensibio H2O', 485000, 100, 'Nước tẩy trang dịu nhẹ Pháp', 'Tẩy trang', 'Da nhạy cảm', 500, '2027-07-15'),
        ('Kem nền Maybelline Fit Me', 245000, 180, 'Kem nền kiềm dầu, mịn lỳ tự nhiên', 'Trang điểm', 'Da hỗn hợp', 30, '2027-04-10'),
        ('Mascara Lancôme Hypnôse', 690000, 55, 'Mascara làm dày mi gấp 6 lần', 'Trang điểm', 'Mọi loại da', 6, '2027-10-20'),
    ],
    'sport': [
        # name, price, stock, desc, category, sport_type, size
        ('Giày chạy bộ Nike Pegasus 40', 3290000, 70, 'Giày running đệm Air Zoom', 'Giày', 'Chạy bộ', '42'),
        ('Áo thun Adidas Climalite', 650000, 150, 'Áo tập gym khô nhanh', 'Quần áo', 'Gym', 'L'),
        ('Bóng đá Adidas Al Rihla', 1450000, 40, 'Bóng thi đấu chính thức World Cup 2022', 'Bóng', 'Bóng đá', 'Size 5'),
        ('Vợt tennis Wilson Pro Staff', 5890000, 20, 'Vợt pro Federer edition', 'Vợt', 'Tennis', '27"'),
        ('Tạ đơn 10kg', 890000, 60, 'Tạ tay bọc cao su 10kg', 'Tạ', 'Tạ', '10kg'),
        ('Xe đạp thể thao Trinx M600', 8900000, 12, 'MTB 21 tốc độ, khung nhôm', 'Xe', 'Đạp xe', '27.5"'),
        ('Dây nhảy thể thao', 185000, 250, 'Dây nhảy tập cardio, có đếm', 'Phụ kiện', 'Cardio', '3m'),
        ('Găng tay boxing Everlast', 1290000, 45, 'Găng boxing pro 16oz', 'Găng', 'Boxing', '16oz'),
        ('Thảm yoga Liforme 4mm', 1890000, 35, 'Thảm yoga cao cấp có căn chỉnh', 'Phụ kiện', 'Yoga', '185x68cm'),
        ('Vợt cầu lông Yonex Astrox 99', 4290000, 25, 'Vợt pro Kento Momota signature', 'Vợt', 'Cầu lông', '4U'),
        ('Bình nước thể thao 1L', 245000, 300, 'Bình giữ nhiệt inox thể thao', 'Phụ kiện', 'Đa năng', '1L'),
    ],
    'stationery': [
        # name, price, stock, desc, category, brand
        ('Bút bi Parker Jotter', 485000, 100, 'Bút bi kim loại cao cấp Pháp', 'Bút', 'Parker'),
        ('Vở ô ly Campus 200 trang', 28000, 500, 'Vở học sinh giấy Bãi Bằng', 'Vở', 'Campus'),
        ('Hộp bút Pilot 12 màu', 185000, 150, 'Bút dạ marker 12 màu nét đôi', 'Bút màu', 'Pilot'),
        ('Máy tính Casio FX-570ES Plus', 520000, 80, 'Máy tính cầm tay thi đại học', 'Máy tính', 'Casio'),
        ('Bảng trắng Flipchart 60x90cm', 480000, 40, 'Bảng văn phòng từ tính 2 mặt', 'Văn phòng', 'Plus'),
        ('Kẹp giấy Deli 100 cái', 32000, 800, 'Kẹp giấy inox các cỡ', 'Văn phòng', 'Deli'),
        ('Băng dính Scotch 3M 24mm', 38000, 600, 'Băng keo trong veo chịu lực', 'Văn phòng', '3M'),
        ('Giấy note Post-it 76x76', 55000, 350, 'Giấy ghi chú 100 tờ dính 3M', 'Văn phòng', '3M'),
        ('Ba lô học sinh MIA', 685000, 120, 'Cặp chống gù, chống nước', 'Balo', 'MIA'),
        ('Bút máy Lamy Safari', 1290000, 50, 'Bút máy học sinh cao cấp Đức', 'Bút', 'Lamy'),
        ('Hộp màu sáp Crayola 64', 285000, 100, 'Sáp màu 64 màu Mỹ', 'Bút màu', 'Crayola'),
    ],
    'appliance': [
        # name, price, stock, desc, category, voltage, warranty_months
        ('Máy giặt Electrolux UltimateCare 9kg', 12990000, 20, 'Máy giặt cửa trước Inverter', 'Máy giặt', '220V', 24),
        ('Tủ lạnh Samsung Side-by-side 650L', 28900000, 10, 'Tủ lạnh 2 cánh Inverter', 'Tủ lạnh', '220V', 24),
        ('Nồi cơm điện Zojirushi 1.8L', 5890000, 30, 'Nồi cơm cao cấp Nhật Bản', 'Nhà bếp', '220V', 12),
        ('Lò vi sóng Panasonic 27L', 3290000, 40, 'Lò vi sóng có nướng Inverter', 'Nhà bếp', '220V', 24),
        ('Máy pha cà phê Delonghi Magnifica', 15990000, 15, 'Máy pha cà phê tự động Ý', 'Nhà bếp', '220V', 24),
        ('Quạt điều hòa Kangaroo 50L', 4890000, 25, 'Quạt hơi nước làm mát 50L', 'Quạt', '220V', 12),
        ('Máy lọc không khí Xiaomi 4 Pro', 6590000, 35, 'Lọc bụi PM2.5, app điều khiển', 'Lọc khí', '220V', 12),
        ('Nồi chiên không dầu Philips 4.1L', 3890000, 45, 'Air fryer RapidAir công nghệ', 'Nhà bếp', '220V', 24),
        ('Bàn ủi hơi nước Tefal', 1890000, 60, 'Bàn ủi hơi công suất 2400W', 'Là ủi', '220V', 12),
        ('Máy hút bụi Dyson V12', 14990000, 18, 'Máy hút bụi không dây Detect', 'Vệ sinh', '220V', 24),
        ('Ấm siêu tốc Xiaomi 1.5L', 585000, 100, 'Ấm đun nước thép không gỉ', 'Nhà bếp', '220V', 12),
    ],
    'jewelry': [
        # name, price, stock, desc, category, material, weight_g
        ('Nhẫn kim cương PNJ 5li', 28900000, 8, 'Nhẫn cầu hôn kim cương GIA', 'Nhẫn', 'Vàng 18K + KC', 3),
        ('Dây chuyền vàng 24K 5 chỉ', 15600000, 12, 'Dây chuyền vàng nguyên chất', 'Dây chuyền', 'Vàng 24K', 18),
        ('Vòng tay bạc Pandora', 2890000, 40, 'Vòng charm Pandora chính hãng', 'Vòng tay', 'Bạc 925', 25),
        ('Bông tai ngọc trai Akoya', 8500000, 15, 'Bông tai ngọc trai thật Nhật', 'Bông tai', 'Vàng 18K + ngọc', 4),
        ('Nhẫn cưới cặp SJC', 18900000, 20, 'Cặp nhẫn cưới vàng 18K trơn', 'Nhẫn', 'Vàng 18K', 8),
        ('Lắc chân bạc ý', 485000, 80, 'Lắc chân bạc ý 925 mảnh', 'Lắc chân', 'Bạc 925', 3),
        ('Đồng hồ Daniel Wellington', 3290000, 35, 'Đồng hồ thời trang Thụy Điển', 'Đồng hồ', 'Thép không gỉ', 40),
        ('Mặt dây chuyền Phật Quan Âm', 5890000, 18, 'Mặt dây chuyền cẩm thạch', 'Dây chuyền', 'Vàng + cẩm thạch', 15),
        ('Nhẫn nam vàng tây', 4890000, 25, 'Nhẫn nam vàng 14K đính đá', 'Nhẫn', 'Vàng 14K', 6),
        ('Bộ trang sức cưới Doji', 45000000, 5, 'Set kiềng + nhẫn + bông tai', 'Set', 'Vàng 24K', 50),
        ('Hoa tai vàng trắng', 6890000, 20, 'Hoa tai vàng trắng đính CZ', 'Bông tai', 'Vàng trắng 14K', 3),
    ],
    'pet-supply': [
        # name, price, stock, desc, category, pet_type, weight_g
        ('Thức ăn Royal Canin chó nhỏ 2kg', 685000, 80, 'Hạt khô cho chó trưởng thành nhỏ', 'Thức ăn', 'Chó', 2000),
        ('Pate Whiskas cho mèo 85g', 18000, 500, 'Pate cá ngừ cho mèo tất cả lứa tuổi', 'Thức ăn', 'Mèo', 85),
        ('Chuồng chó inox size L', 1890000, 25, 'Chuồng chó inox 304 có khay', 'Chuồng', 'Chó', 5000),
        ('Cát vệ sinh mèo Cat\'s Best 10L', 385000, 120, 'Cát đậu nành khử mùi', 'Vệ sinh', 'Mèo', 4500),
        ('Đồ chơi KONG Classic', 385000, 100, 'Đồ chơi gặm cao su bền', 'Đồ chơi', 'Chó', 200),
        ('Dây dắt chó Pettorina', 245000, 150, 'Dây dắt 2m chống kéo', 'Phụ kiện', 'Chó', 150),
        ('Bình lọc bể cá 300L/h', 485000, 45, 'Máy lọc bể cá treo thành 300L/h', 'Cá cảnh', 'Cá', 500),
        ('Lồng chim vành khuyên', 285000, 60, 'Lồng chim tre truyền thống', 'Lồng', 'Chim', 1000),
        ('Cỏ lúa mạch cho thỏ 500g', 85000, 200, 'Cỏ timothy khô cho thỏ hamster', 'Thức ăn', 'Thỏ', 500),
        ('Sữa tắm Bioline cho chó 500ml', 245000, 180, 'Sữa tắm khử mùi mượt lông', 'Tắm rửa', 'Chó', 500),
        ('Bể cá thủy tinh 40L', 785000, 35, 'Bể cá kính cong 40L kèm đèn LED', 'Cá cảnh', 'Cá', 10000),
    ],
}


def payload_for(ptype, row):
    base = {
        'name': row[0],
        'price': str(row[1]),
        'stock': row[2],
        'description': row[3],
        'category': row[4],
        'image_url': f"https://loremflickr.com/400/400/{ptype}?lock={hash(row[0]) & 0xffff}",
    }
    if ptype == 'electronic':
        base.update({'brand': row[5], 'warranty_months': row[6], 'power_w': row[7]})
    elif ptype == 'food':
        base.update({'origin': row[5], 'weight_g': row[6], 'expiry_date': row[7]})
    elif ptype == 'toy':
        base.update({'age_range': row[5], 'material': row[6]})
    elif ptype == 'furniture':
        base.update({'dimensions': row[5], 'material': row[6], 'color': row[7]})
    elif ptype == 'cosmetic':
        base.update({'skin_type': row[5], 'volume_ml': row[6], 'expiry_date': row[7]})
    elif ptype == 'sport':
        base.update({'sport_type': row[5], 'size': row[6]})
    elif ptype == 'stationery':
        base.update({'brand': row[5]})
    elif ptype == 'appliance':
        base.update({'voltage': row[5], 'warranty_months': row[6]})
    elif ptype == 'jewelry':
        base.update({'material': row[5], 'weight_g': row[6]})
    elif ptype == 'pet-supply':
        base.update({'pet_type': row[5], 'weight_g': row[6]})
    return base


def seed_products():
    section('Seed 10 product-service')
    for port, plural, ptype in SERVICES:
        rows = PRODUCT_DATA[ptype]
        url = f'http://localhost:{port}/{plural}/'
        success = 0
        skipped = 0
        for row in rows:
            data = payload_for(ptype, row)
            resp, code = post(url, data)
            if code in (200, 201):
                success += 1
            elif code == 400 and 'unique' in str(resp).lower():
                skipped += 1
            else:
                err(f'{ptype}: "{row[0][:40]}" http={code} {resp}')
        ok(f'{ptype:12s} seeded={success} skipped={skipped} total={len(rows)}')


# ────────────────────────────────────────────────────────
# USERS
# ────────────────────────────────────────────────────────

HO = ['Nguyễn', 'Trần', 'Lê', 'Phạm', 'Hoàng', 'Huỳnh', 'Phan', 'Vũ', 'Võ', 'Đặng',
      'Bùi', 'Đỗ', 'Hồ', 'Ngô', 'Dương', 'Lý']
TEN_DEM = ['Văn', 'Thị', 'Minh', 'Quang', 'Thanh', 'Hoàng', 'Ngọc', 'Thu', 'Hữu',
           'Đức', 'Thành', 'Kim', 'Tuấn', 'Bảo']
TEN = ['An', 'Bình', 'Chi', 'Dũng', 'Giang', 'Hà', 'Hải', 'Hạnh', 'Hiếu', 'Hòa',
       'Hùng', 'Huy', 'Hương', 'Khánh', 'Lan', 'Linh', 'Long', 'Mai', 'Minh',
       'Nam', 'Ngân', 'Nhi', 'Phong', 'Phúc', 'Quân', 'Quỳnh', 'Sơn', 'Tâm',
       'Thảo', 'Thu', 'Tiến', 'Trang', 'Trung', 'Tú', 'Tuấn', 'Vy', 'Yến']


def slugify(s):
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', s)
    only_ascii = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return only_ascii.replace('đ', 'd').replace('Đ', 'D').lower()


def seed_users(n=500):
    section(f'Seed {n} users')
    # Lấy job list để random
    try:
        r = requests.get(f'{CUSTOMER_URL}/jobs/', timeout=5)
        jobs = r.json() if r.status_code == 200 else []
        job_ids = [j['id'] for j in jobs] if isinstance(jobs, list) else []
    except Exception:
        job_ids = []
    info(f'jobs available: {len(job_ids)}')

    success = 0
    skipped = 0
    errs = 0
    for i in range(n):
        ho = random.choice(HO)
        td = random.choice(TEN_DEM)
        tn = random.choice(TEN)
        full_name = f'{ho} {td} {tn}'
        email = f'{slugify(tn)}.{slugify(ho)}{i:04d}@example.com'
        data = {
            'name': full_name,
            'email': email,
            'password': 'password123',
        }
        if job_ids:
            data['job'] = random.choice(job_ids)
        resp, code = post(f'{CUSTOMER_URL}/customers/', data)
        if code in (200, 201):
            success += 1
        elif code == 400:
            skipped += 1
        else:
            errs += 1
            if errs <= 3:
                err(f'user {i}: http={code} {resp}')
        if (i + 1) % 100 == 0:
            info(f'{i+1}/{n} processed (ok={success} dup={skipped} err={errs})')
    ok(f'total ok={success} duplicate={skipped} error={errs}')


def main():
    t0 = time.time()
    seed_products()
    seed_users(500)
    print(f'\nDONE in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
