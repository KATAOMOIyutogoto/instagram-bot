import cv2
import numpy as np

# 画像を読み込み
img1 = cv2.imread("image1.jpg")
img2 = cv2.imread("image2.jpg")

# サイズが違えば比較不能（False）
if img1.shape != img2.shape:
    print("❌ サイズが違うため一致しません")
else:
    # ピクセル単位で完全一致しているかチェック
    if np.array_equal(img1, img2):
        print("✅ 完全に一致しています")
    else:
        print("❌ 内容が異なります")
