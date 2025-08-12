# 🔧 HƯỚNG DẪN ĐỒNG BỘ DATABASE VÀ VECTOR STORE

## 🧩 Vấn đề hiện tại
- **Database SQLite**: 0 entries (trống sau khi bạn xóa)
- **Vector Store**: Vẫn còn 3 documents cũ (chưa đồng bộ)
- **Kết quả**: RAG system vẫn trả lời dựa trên dữ liệu cũ đã bị xóa

## ✅ Đã sửa
- **Fast Mode Error**: Đã thêm method `format_documents_for_context` vào `Retrieval_And_Generator.py`
- **Cleanup Tool**: Tạo script `clean_vector_db.py` để xóa vector database

## 🔧 Cách khắc phục

### Bước 1: Đóng tất cả ứng dụng
```bash
# Đóng Streamlit app (Ctrl+C)
# Đóng VS Code terminals đang chạy Python
# Hoặc restart VS Code
```

### Bước 2: Chạy cleanup script
```bash
python clean_vector_db.py
```

### Bước 3: Có 2 lựa chọn

#### Lựa chọn A: Bắt đầu mới (Recommended)
- Vector database đã được xóa clean
- Database SQLite đã trống
- Có thể thêm diary mới và indexing sẽ tự động tạo vector store mới

#### Lựa chọn B: Khôi phục dữ liệu cũ
Nếu bạn vô tình xóa và muốn khôi phục:
1. Restore database từ backup
2. Chạy lại indexing pipeline:
```bash
python src/Indexingstep/run_indexing.py
```

## 🚀 Test Fast Mode
Sau khi cleanup, test fast mode:
```bash
cd src/streamlit_app
streamlit run interface.py
```

Trong UI:
- ✅ Checkbox "Fast Mode" hoạt động
- ⚡ Response nhanh hơn với Fast Mode
- 📊 Performance indicator hiển thị mode hiện tại

## 🎯 Kết quả mong đợi
- Database và Vector Store đồng bộ (cùng 0 hoặc cùng số lượng entries)
- Fast Mode hoạt động không lỗi
- Response time cải thiện với Fast Mode

## 🐛 Nếu vẫn có lỗi
1. Check log files trong `src/Indexingstep/indexing.log`
2. Verify API key Google Generative AI
3. Run test với: `python check_db.py`

---
*Cleanup tool sẽ tự động detect sync issues và recommend actions*
