# Hệ Thống Xử Lý Video Tự Động - Phân Tách Shot và Quản Lý Metadata

## 🎯 Tổng Quan

Hệ thống này thực hiện **tự động phân tách video thành các shot nhỏ** và **trích xuất metadata chi tiết** cho mỗi shot, sau đó lưu trữ trong thư viện có tổ chức và cơ sở dữ liệu để phục vụ cho việc quản lý, tìm kiếm và dựng video tự động trong tương lai.

### ✅ Các Tính Năng Chính

1. **Tải Video Tự Động**: Hỗ trợ tải video từ YouTube và các nguồn khác
2. **Phân Tách Shot Thông Minh**: Sử dụng AI và Computer Vision để phát hiện chuyển cảnh
3. **Trích Xuất Metadata Toàn Diện**: 
   - Thông tin kỹ thuật (độ phân giải, FPS, codec...)
   - Phân tích hình ảnh (độ sáng, độ tương phản, màu sắc, chuyển động...)
   - Phân tích âm thanh (có giọng nói, loại âm thanh, tempo...)
   - Phân tích nội dung bằng AI (mô tả cảnh, nhận diện đối tượng...)
4. **Tổ Chức Thư Viện Thông Minh**: Sắp xếp file theo nhiều tiêu chí
5. **Cơ Sở Dữ Liệu Mạnh Mẽ**: Lưu trữ và tìm kiếm metadata hiệu quả
6. **Giao Diện Dòng Lệnh Linh Hoạt**: Dễ sử dụng và tự động hóa

## 🏗️ Kiến Trúc Hệ Thống

```
video_processor.py (Main Pipeline)
├── core/
│   ├── video_downloader.py     # Tải video từ URL
│   ├── shot_detector.py        # Phát hiện và tách shot
│   ├── metadata_extractor.py   # Trích xuất metadata
│   ├── database_manager.py     # Quản lý cơ sở dữ liệu
│   └── library_manager.py      # Quản lý tổ chức file
├── library/                    # Thư viện video được tổ chức
│   ├── raw_videos/            # Video gốc
│   ├── shots/                 # Video shot đã tách
│   ├── thumbnails/            # Hình thumbnail
│   ├── metadata/              # File metadata JSON
│   └── exports/               # Gói xuất khẩu
└── config files & documentation
```

## 📋 Yêu Cầu Hệ Thống

### Phần Mềm Cần Thiết
- **Python 3.8+**
- **MySQL/MariaDB** (cho cơ sở dữ liệu)
- **FFmpeg** (cho xử lý video)

### Thư Viện Python
Xem file `requirements.txt` để có danh sách đầy đủ. Các thư viện chính:
- `opencv-python` - Xử lý hình ảnh và video
- `yt-dlp` - Tải video từ YouTube
- `librosa` - Phân tích âm thanh
- `transformers` - AI models cho phân tích nội dung
- `mysql-connector-python` - Kết nối cơ sở dữ liệu
- `scikit-learn` - Machine learning
- `tqdm` - Progress bars

## 🚀 Cài Đặt

### 1. Clone Repository
```bash
git clone <repository-url>
cd video-processing-system
```

### 2. Cài Đặt Dependencies
```bash
# Tạo virtual environment (khuyến nghị)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate     # Windows

# Cài đặt packages
pip install -r requirements.txt
```

### 3. Cài Đặt FFmpeg
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: Tải từ https://ffmpeg.org/download.html
```

### 4. Thiết Lập Cơ Sở Dữ Liệu
```bash
# Tạo database MySQL
mysql -u root -p
CREATE DATABASE video_library CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Import schema
mysql -u root -p video_library < database.sql
```

### 5. Cấu Hình
```bash
# Copy file cấu hình mẫu
cp .env.example .env
cp config.json.example config.json

# Chỉnh sửa thông tin database trong .env
DB_HOST=localhost
DB_NAME=video_library
DB_USER=root
DB_PASSWORD=your_password
```

## 💻 Sử Dụng

### Xử Lý Video Từ URL
```bash
# Xử lý một video YouTube
python video_processor.py --url "https://www.youtube.com/watch?v=VIDEO_ID"

# Xử lý nhiều video từ file
echo "https://www.youtube.com/watch?v=VIDEO1" > urls.txt
echo "https://www.youtube.com/watch?v=VIDEO2" >> urls.txt
python video_processor.py --urls-file urls.txt --output results.json
```

### Xử Lý Video Local
```bash
python video_processor.py --video-file "/path/to/video.mp4"
```

### Tìm Kiếm Thư Viện
```bash
# Tìm shot có âm thanh, thời lượng 2-10 giây
python video_processor.py --search --has-audio --min-duration 2 --max-duration 10

# Tìm theo keywords
python video_processor.py --search --keywords "speech,high_quality" --output search_results.json

# Tìm shot có giọng nói
python video_processor.py --search --has-speech --min-quality 0.7
```

### Xem Thống Kê
```bash
python video_processor.py --stats --output library_stats.json
```

### Xuất Khẩu Shots
```bash
# Xuất các shot cụ thể
python video_processor.py --export "shot_001,shot_002,shot_003"
```

### Tìm Duplicate
```bash
python video_processor.py --find-duplicates --output duplicates.json
```

## 📊 Metadata Được Trích Xuất

### 1. Thông Tin Kỹ Thuật
- Độ phân giải (width x height)
- Frame rate (FPS)
- Codec video
- Bitrate
- Thời lượng chính xác
- Kích thước file

### 2. Phân Tích Hình Ảnh
- **Độ sáng**: Trung bình, min, max và phân loại
- **Độ tương phản**: Mức độ và phân loại
- **Chuyển động**: Phân tích optical flow và phân loại
- **Màu sắc**: Màu chủ đạo và độ đa dạng màu
- **Chất lượng**: Điểm số tổng thể (0-1)

### 3. Phân Tích Âm Thanh
- Có âm thanh hay không
- Phát hiện giọng nói
- Phân loại loại âm thanh (speech, music, ambient...)
- Âm lượng và phân loại
- Đặc trưng MFCC
- Tempo và nhịp điệu
- Spectral features

### 4. Phân Tích Nội Dung (AI)
- **Mô tả cảnh**: Sử dụng BLIP model
- **Nhận diện đối tượng**: Phát hiện face, objects
- **Phân loại cảnh**: bright_scene, dark_scene, complex_scene...
- **Keywords tự động**: Dựa trên tất cả metadata

## 🗂️ Tổ Chức Thư Viện

### Cấu Trúc Thư Mục
```
library/
├── raw_videos/           # Video gốc được tổ chức theo uploader/năm/tháng
├── shots/
│   ├── by_date/         # Shots theo ngày tạo
│   ├── by_source/       # Shots theo nguồn video
│   ├── by_quality/      # Shots theo chất lượng (high/medium/low)
│   ├── by_duration/     # Shots theo thời lượng
│   └── by_type/         # Shots theo loại (speech/music/silent)
├── thumbnails/          # Thumbnail được tổ chức theo năm/tháng
├── metadata/            # File JSON metadata
├── exports/             # Gói xuất khẩu
└── backups/            # Backup metadata
```

### Symbolic Links
Hệ thống tạo symbolic links để tổ chức shots theo nhiều tiêu chí mà không tốn dung lượng:
- File gốc được lưu trong `shots/by_date/`
- Các links được tạo trong `by_quality/`, `by_duration/`, `by_type/`, `by_source/`

## 🔍 Tìm Kiếm và Lọc

### Các Tiêu Chí Tìm Kiếm
- **Thời lượng**: `min_duration`, `max_duration`
- **Chất lượng**: `min_quality` (0-1)
- **Độ phân giải**: `resolution` (ví dụ: "1920x1080")
- **Chuyển động**: `motion_category` (high/medium/low)
- **Âm thanh**: `has_audio`, `has_speech`
- **Loại âm thanh**: `audio_type`
- **Loại cảnh**: `scene_type`
- **Keywords**: `keywords` (danh sách)
- **Tìm kiếm text**: `caption_search` (trong mô tả AI)
- **Video nguồn**: `source_video_id`

### Ví Dụ Tìm Kiếm Nâng Cao
```python
from core.database_manager import DatabaseManager

db = DatabaseManager()

# Tìm shots chất lượng cao có giọng nói, thời lượng 3-8 giây
results = db.search_shots({
    'min_quality': 0.8,
    'has_speech': True,
    'min_duration': 3.0,
    'max_duration': 8.0,
    'motion_category': 'medium'
}, limit=20)

print(f"Tìm thấy {len(results)} shots phù hợp")
```

## 📈 Monitoring và Thống Kê

### Database Statistics
- Tổng số video nguồn và shots
- Thống kê thời lượng
- Phân bố chất lượng
- Phân bố độ phân giải
- Thống kê âm thanh
- Top keywords

### File System Statistics
- Dung lượng sử dụng
- Số lượng files theo loại
- Cấu trúc thư mục
- Tổ chức shots

## 🔧 Cấu Hình Nâng Cao

### File config.json
```json
{
  "shot_detection": {
    "threshold": 0.3,           // Ngưỡng phát hiện chuyển cảnh
    "min_shot_duration": 1.0,   // Thời lượng shot tối thiểu
    "max_shot_duration": 30.0,  // Thời lượng shot tối đa
    "use_optical_flow": true,   // Sử dụng optical flow
    "use_edge_detection": true  // Sử dụng edge detection
  },
  "metadata_extraction": {
    "use_ai_analysis": true,    // Bật phân tích AI
    "histogram_bins": 256       // Số bins cho histogram
  },
  "processing": {
    "batch_size": 5,           // Số shot xử lý cùng lúc
    "max_concurrent": 2        // Số luồng xử lý song song
  }
}
```

### Tùy Chỉnh Shot Detection
```python
from core.shot_detector import ShotDetector

detector = ShotDetector()
detector.threshold = 0.4          # Tăng độ nhạy
detector.min_shot_duration = 2.0  # Shot tối thiểu 2 giây
detector.use_optical_flow = True  # Bật optical flow
```

## 🚨 Xử Lý Lỗi

### Lỗi Thường Gặp

1. **Lỗi Database Connection**
   ```
   Error connecting to MySQL: Access denied
   ```
   → Kiểm tra thông tin database trong `.env`

2. **Lỗi FFmpeg Not Found**
   ```
   FileNotFoundError: ffmpeg
   ```
   → Cài đặt FFmpeg và thêm vào PATH

3. **Lỗi Out of Memory**
   ```
   MemoryError during video processing
   ```
   → Giảm `batch_size` trong config

4. **Lỗi AI Models**
   ```
   Failed to load AI models
   ```
   → Đặt `use_ai_analysis: false` nếu không cần AI

### Debug Mode
```bash
# Chạy với log chi tiết
python video_processor.py --url "..." --config debug_config.json

# Xem log file
tail -f video_processor.log
```

## 📝 API và Tích Hợp

### Sử Dụng Như Library
```python
from video_processor import VideoProcessor

# Khởi tạo
processor = VideoProcessor()

# Xử lý video
result = processor.process_video_url("https://youtube.com/watch?v=...")

# Tìm kiếm
shots = processor.search_library({
    'has_speech': True,
    'min_quality': 0.7
})

# Thống kê
stats = processor.get_library_stats()
```

### Tích Hợp với Existing System
```python
# Chỉ sử dụng shot detection
from core.shot_detector import ShotDetector

detector = ShotDetector()
shots = detector.process_video("/path/to/video.mp4")

# Chỉ sử dụng metadata extraction
from core.metadata_extractor import MetadataExtractor

extractor = MetadataExtractor()
metadata = extractor.extract_shot_metadata(shot_info)
```

## 🔮 Tương Lai và Mở Rộng

### Tính Năng Sắp Tới
- [ ] Web interface cho quản lý thư viện
- [ ] API REST cho tích hợp
- [ ] Hỗ trợ nhiều định dạng video hơn
- [ ] Phân tích emotion và sentiment
- [ ] Auto-tagging thông minh hơn
- [ ] Video similarity matching
- [ ] Batch processing với queue system

### Customization Points
- **Custom shot detection algorithms**: Thêm thuật toán phát hiện shot mới
- **Custom metadata extractors**: Thêm loại metadata mới
- **Custom organization schemes**: Thêm cách tổ chức file mới
- **Custom AI models**: Sử dụng models khác cho phân tích nội dung

## 🤝 Đóng Góp

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Tạo Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 📞 Hỗ Trợ

- **Issues**: Tạo issue trên GitHub
- **Documentation**: Xem thêm trong thư mục `docs/`
- **Examples**: Xem thư mục `examples/`

---

## 📋 Checklist Triển Khai

- [ ] Cài đặt Python 3.8+
- [ ] Cài đặt MySQL/MariaDB
- [ ] Cài đặt FFmpeg
- [ ] Clone repository và cài đặt dependencies
- [ ] Tạo database và import schema
- [ ] Cấu hình `.env` và `config.json`
- [ ] Test với một video mẫu
- [ ] Thiết lập backup tự động (khuyến nghị)
- [ ] Cấu hình monitoring (tùy chọn)

Chúc bạn sử dụng hệ thống hiệu quả! 🎬✨