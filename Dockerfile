# Sử dụng image Python chính thức
FROM python:3.10-slim

# Đặt thư mục làm việc trong container
WORKDIR /app

# Sao chép file requirements.txt vào container (nếu có)
COPY requirements.txt .

# Cài đặt các thư viện phụ thuộc
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Chạy ứng dụng (thay main.py bằng file chạy chính của bạn)
CMD ["python", "app.py"]