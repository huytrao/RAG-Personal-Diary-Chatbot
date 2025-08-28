# Sử dụng image Python chính thức
FROM python:3.11.9-slim

# Đặt thư mục làm việc trong container
WORKDIR /app

# Sao chép file requirements.txt vào container
COPY requirements.txt .

# Cài đặt các thư viện phụ thuộc
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Tạo thư mục VectorDB và cấp quyền ghi
RUN mkdir -p /app/src/VectorDB && chmod -R 777 /app/src/VectorDB
RUN mkdir -p /app/logs && chmod -R 777 /app/logs
# Chạy ứng dụng
CMD ["python", "app.py"]
