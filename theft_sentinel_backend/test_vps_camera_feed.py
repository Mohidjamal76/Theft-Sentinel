import cv2

cap = cv2.VideoCapture("http://157.245.111.63:8889/cam2")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame")
        break
    print(ret)