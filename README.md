# Infinite Flyer — Assignment 3

## Mô tả
"Infinite Flyer" là một game flappy-style đơn giản viết bằng Python + Pygame. Người chơi điều khiển một sinh vật (bird/dragon) liên tục vỗ cánh để né chướng ngại vật và cố gắng sống sót càng lâu càng tốt.

## Tính năng chính
- Cơ chế "Tap to Flap" (chạm/nhấn để vỗ cánh)
- Chướng ngại vật động (Dynamic Obstacles)
- Hệ thống hạt/particle cho hiệu ứng (Particle Systems)
- Điều chỉnh độ khó theo thời gian (Difficulty Scaling)

## Yêu cầu
- Python 3.8 hoặc mới hơn
- Các thư viện trong `requirements.txt` (chủ yếu là `pygame`)

## Cài đặt
1. Tạo môi trường ảo (khuyến nghị):

```bash
python -m venv venv
venv\Scripts\activate
```

2. Cài đặt phụ thuộc:

```bash
pip install -r requirements.txt
```

## Chạy game

```bash
python main.py
```

## Điều khiển
- Nhấn phím `Space` hoặc click/tap để vỗ cánh.
- Nhấn `Esc` để thoát.

## Cấu trúc dự án (tóm tắt)
- `main.py` — điểm vào chương trình
- `config.py` — cấu hình game
- `sprites.py` — lớp sprite và logic đối tượng
- `assets/` — hình ảnh, âm thanh và tài nguyên

## Ghi chú phát triển
- Các phần mở rộng cần triển khai cho bài tập: Dynamic Obstacles, Particle Systems, Difficulty Scaling.
- Các sprite có thể tìm thấy trong `assets/dragon/PNG` và `assets/bird/PNG`.

## Credits & License
- Một số tài nguyên hình ảnh lấy từ bevouliin_dot_com (xem `assets/dragon/get more at bevouliin_dot_com.txt`).

