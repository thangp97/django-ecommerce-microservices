"""Train 3 sequence models (RNN, LSTM, biLSTM) cho next-category prediction.

Input : 7 hanh vi gan nhat cua user
        - product_type   (12 class, embed 16-d)
        - action         (3 class,  embed 4-d)
        - global_pid     (ptype+id, embed 24-d)   <- NEW
        - delta_log_hour (scalar)                 <- NEW
Output: product_type cua hanh vi tiep theo (12 class).

Ket qua:
  - models/model_best.keras
  - plots/*.png
  - In bang so sanh + classification report
"""
import os
import random

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.callbacks import EarlyStopping

# ---------- Reproducibility ----------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)

# ---------- Config ----------
CSV_FILE = 'data_user500.csv'
SEQ_LEN = 7
EPOCHS = 50
BATCH_SIZE = 64
EMB_PT = 16
EMB_ACT = 4
EMB_PID = 24
HIDDEN = 96
OUT_DIR_MODELS = 'models'
OUT_DIR_PLOTS = 'plots'
os.makedirs(OUT_DIR_MODELS, exist_ok=True)
os.makedirs(OUT_DIR_PLOTS, exist_ok=True)


# =========================================================
# 1) Load & preprocess
# =========================================================
def load_and_encode(csv_path):
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(['user_id', 'timestamp']).reset_index(drop=True)

    # product_type -> id
    ptypes = sorted(df['product_type'].unique())
    actions = sorted(df['action'].unique())
    pt2id = {v: i for i, v in enumerate(ptypes)}
    act2id = {v: i for i, v in enumerate(actions)}
    df['pt_id'] = df['product_type'].map(pt2id)
    df['act_id'] = df['action'].map(act2id)

    # global product id = unique (product_type, product_id)
    df['pp_key'] = df['product_type'] + '#' + df['product_id'].astype(str)
    pp_keys = sorted(df['pp_key'].unique())
    pp2id = {k: i for i, k in enumerate(pp_keys)}
    df['gpid'] = df['pp_key'].map(pp2id)

    # time_delta giua 2 hanh vi lien tiep cua CUNG user (log-hour)
    df['delta_h'] = (
        df.groupby('user_id')['timestamp'].diff().dt.total_seconds() / 3600.0
    ).fillna(0.0)
    df['delta_log'] = np.log1p(df['delta_h'].clip(lower=0.0))

    return df, pt2id, act2id, pp2id


def make_sliding_windows(df, seq_len):
    X_pt, X_act, X_pid, X_td, y = [], [], [], [], []
    for _, g in df.groupby('user_id'):
        pts = g['pt_id'].to_list()
        acts = g['act_id'].to_list()
        gpids = g['gpid'].to_list()
        tds = g['delta_log'].to_list()
        for i in range(len(pts) - seq_len):
            X_pt.append(pts[i : i + seq_len])
            X_act.append(acts[i : i + seq_len])
            X_pid.append(gpids[i : i + seq_len])
            X_td.append(tds[i : i + seq_len])
            y.append(pts[i + seq_len])
    return (
        np.array(X_pt, dtype=np.int32),
        np.array(X_act, dtype=np.int32),
        np.array(X_pid, dtype=np.int32),
        np.array(X_td, dtype=np.float32),
        np.array(y, dtype=np.int32),
    )


def split_by_user(user_ids, train_frac=0.7, val_frac=0.15):
    ids = np.array(sorted(set(user_ids)))
    rng = np.random.default_rng(SEED)
    rng.shuffle(ids)
    n = len(ids)
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)
    return (
        set(ids[:n_train]),
        set(ids[n_train : n_train + n_val]),
        set(ids[n_train + n_val :]),
    )


# =========================================================
# 2) Models
# =========================================================
def build_model(arch, n_ptypes, n_actions, n_pp, seq_len):
    pt_in = layers.Input(shape=(seq_len,), name='pt', dtype='int32')
    act_in = layers.Input(shape=(seq_len,), name='action', dtype='int32')
    pid_in = layers.Input(shape=(seq_len,), name='pid', dtype='int32')
    td_in = layers.Input(shape=(seq_len,), name='td', dtype='float32')

    pt_emb = layers.Embedding(n_ptypes, EMB_PT, name='pt_emb')(pt_in)
    act_emb = layers.Embedding(n_actions, EMB_ACT, name='act_emb')(act_in)
    pid_emb = layers.Embedding(n_pp, EMB_PID, name='pid_emb')(pid_in)
    td_ex = layers.Reshape((seq_len, 1))(td_in)

    x = layers.Concatenate(axis=-1)([pt_emb, act_emb, pid_emb, td_ex])

    if arch == 'rnn':
        x = layers.SimpleRNN(HIDDEN)(x)
    elif arch == 'lstm':
        x = layers.LSTM(HIDDEN)(x)
    elif arch == 'bilstm':
        x = layers.Bidirectional(layers.LSTM(HIDDEN))(x)
    else:
        raise ValueError(arch)

    x = layers.Dropout(0.3)(x)
    x = layers.Dense(64, activation='relu')(x)
    x = layers.Dropout(0.2)(x)
    out = layers.Dense(n_ptypes, activation='softmax')(x)

    m = Model(inputs=[pt_in, act_in, pid_in, td_in], outputs=out, name=arch)
    m.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy'],
    )
    return m


# =========================================================
# 3) Training pipeline
# =========================================================
def main():
    print('=== Load data ===')
    df, pt2id, act2id, pp2id = load_and_encode(CSV_FILE)
    n_ptypes = len(pt2id)
    n_actions = len(act2id)
    n_pp = len(pp2id)
    print(f'  rows={len(df)}  n_ptypes={n_ptypes}  n_actions={n_actions}  n_products={n_pp}')

    X_pt, X_act, X_pid, X_td, y = make_sliding_windows(df, SEQ_LEN)
    print(f'  samples={len(y)}  seq_len={SEQ_LEN}')

    # map sample -> user de split no leak
    sample_users = []
    for uid, g in df.groupby('user_id'):
        sample_users.extend([uid] * max(0, len(g) - SEQ_LEN))
    sample_users = np.array(sample_users)

    train_u, val_u, test_u = split_by_user(df['user_id'].unique())
    m_tr = np.isin(sample_users, list(train_u))
    m_va = np.isin(sample_users, list(val_u))
    m_te = np.isin(sample_users, list(test_u))
    print(f'  train={m_tr.sum()}  val={m_va.sum()}  test={m_te.sum()}')

    def pack(mask):
        return ([X_pt[mask], X_act[mask], X_pid[mask], X_td[mask]], y[mask])

    (Xtr, ytr) = pack(m_tr)
    (Xva, yva) = pack(m_va)
    (Xte, yte) = pack(m_te)

    histories = {}
    test_metrics = {}
    models = {}
    for arch in ['rnn', 'lstm', 'bilstm']:
        print(f'\n=== Train {arch.upper()} ===')
        m = build_model(arch, n_ptypes, n_actions, n_pp, SEQ_LEN)
        m.summary(line_length=80)
        es = EarlyStopping(monitor='val_loss', patience=7, restore_best_weights=True)
        h = m.fit(
            Xtr, ytr,
            validation_data=(Xva, yva),
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            callbacks=[es],
            verbose=2,
        )
        histories[arch] = h.history
        models[arch] = m

        y_pred = m.predict(Xte, verbose=0).argmax(axis=1)
        acc = accuracy_score(yte, y_pred)
        f1 = f1_score(yte, y_pred, average='macro', zero_division=0)
        test_metrics[arch] = {'accuracy': acc, 'f1_macro': f1, 'y_pred': y_pred}
        print(f'  [TEST] acc={acc:.4f}  f1_macro={f1:.4f}')

    # ---------- Plots ----------
    print('\n=== Plot ===')
    plt.figure(figsize=(10, 4))
    for arch, h in histories.items():
        plt.plot(h['loss'], label=f'{arch} train')
        plt.plot(h['val_loss'], '--', label=f'{arch} val')
    plt.title('Loss per epoch')
    plt.xlabel('epoch'); plt.ylabel('loss'); plt.legend(fontsize=8); plt.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(f'{OUT_DIR_PLOTS}/loss_curves.png', dpi=120); plt.close()

    plt.figure(figsize=(10, 4))
    for arch, h in histories.items():
        plt.plot(h['accuracy'], label=f'{arch} train')
        plt.plot(h['val_accuracy'], '--', label=f'{arch} val')
    plt.title('Accuracy per epoch')
    plt.xlabel('epoch'); plt.ylabel('accuracy'); plt.legend(fontsize=8); plt.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(f'{OUT_DIR_PLOTS}/accuracy_curves.png', dpi=120); plt.close()

    archs = list(test_metrics.keys())
    accs = [test_metrics[a]['accuracy'] for a in archs]
    f1s = [test_metrics[a]['f1_macro'] for a in archs]
    x = np.arange(len(archs))
    plt.figure(figsize=(7, 4))
    plt.bar(x - 0.2, accs, width=0.4, label='accuracy')
    plt.bar(x + 0.2, f1s, width=0.4, label='f1 macro')
    plt.xticks(x, [a.upper() for a in archs])
    plt.ylim(0, 1); plt.title('Test performance'); plt.legend(); plt.grid(axis='y', alpha=0.3)
    for i, (a, f) in enumerate(zip(accs, f1s)):
        plt.text(i - 0.2, a + 0.01, f'{a:.3f}', ha='center', fontsize=8)
        plt.text(i + 0.2, f + 0.01, f'{f:.3f}', ha='center', fontsize=8)
    plt.tight_layout(); plt.savefig(f'{OUT_DIR_PLOTS}/test_bars.png', dpi=120); plt.close()

    best = max(test_metrics, key=lambda a: test_metrics[a]['f1_macro'])
    cm = confusion_matrix(yte, test_metrics[best]['y_pred'])
    labels = [k for k, _ in sorted(pt2id.items(), key=lambda kv: kv[1])]
    plt.figure(figsize=(7, 6))
    plt.imshow(cm, cmap='Blues')
    plt.title(f'Confusion matrix ({best.upper()})')
    plt.xticks(range(n_ptypes), labels, rotation=45, ha='right', fontsize=8)
    plt.yticks(range(n_ptypes), labels, fontsize=8)
    plt.xlabel('pred'); plt.ylabel('true')
    for i in range(n_ptypes):
        for j in range(n_ptypes):
            v = cm[i, j]
            if v:
                plt.text(j, i, str(v), ha='center', va='center',
                         fontsize=7, color='white' if v > cm.max() / 2 else 'black')
    plt.colorbar()
    plt.tight_layout(); plt.savefig(f'{OUT_DIR_PLOTS}/confusion_best.png', dpi=120); plt.close()

    # ---------- Save best ----------
    best_path = f'{OUT_DIR_MODELS}/model_best.keras'
    models[best].save(best_path)
    print(f'  [OK] best={best.upper()}  saved -> {best_path}')

    print('\n=== Test report (best model) ===')
    print(classification_report(yte, test_metrics[best]['y_pred'],
          target_names=labels, zero_division=0, digits=3))

    print('\n=== Danh gia bang loi ===')
    for a in archs:
        m = test_metrics[a]
        print(f'  {a.upper():<7}  acc={m["accuracy"]:.4f}  f1_macro={m["f1_macro"]:.4f}')
    print(f'\n=> Model tot nhat: {best.upper()}')
    _explain(best, test_metrics)


def _explain(best, metrics):
    rnn = metrics['rnn']
    lstm = metrics['lstm']
    bilstm = metrics['bilstm']
    print(
        'Nhan xet:\n'
        f'- RNN     : acc={rnn["accuracy"]:.3f}, f1={rnn["f1_macro"]:.3f} '
        '— kien truc don gian, vanishing gradient o chuoi dai.\n'
        f'- LSTM    : acc={lstm["accuracy"]:.3f}, f1={lstm["f1_macro"]:.3f} '
        '— cong gate giu context xa, thuong vuot RNN.\n'
        f'- biLSTM  : acc={bilstm["accuracy"]:.3f}, f1={bilstm["f1_macro"]:.3f} '
        '— them chieu nguoc, bat cau truc 2 phia nhung de overfit.\n'
        f'=> Chon {best.upper()} lam model_best vi F1-macro cao nhat '
        '(12 class khong can bang nen f1-macro thich hop hon accuracy).'
    )


if __name__ == '__main__':
    main()
