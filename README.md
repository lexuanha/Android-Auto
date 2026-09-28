# Android Termux Automation Test

Tài liệu này ghi lại thiết lập và kết quả thử chạy Python trên điện thoại Android bằng Termux. ADB từ máy tính chỉ dùng để cài/kiểm tra thiết bị, chép script và hỗ trợ khởi chạy; Python thực sự chạy bên trong Termux trên điện thoại.

## Mục tiêu

- Gửi tin nhắn Telegram qua Bot API từ Android, một tin mỗi 3 phút.
- Kiểm tra script có tiếp tục chạy khi khóa màn hình hay không.
- Dừng lượt thử từ Telegram bằng lệnh `/stop`.
- Làm cơ sở cho các thử nghiệm nhận lệnh `/test` và `/task` sau này.

Đây là thử nghiệm khả thi, không phải dịch vụ được đảm bảo luôn chạy. Android có thể trì hoãn mạng hoặc kết thúc tiến trình nền do Doze, giới hạn pin, khởi động lại hoặc chính sách riêng của nhà sản xuất.

## Thành phần

- `telegram_test.py`: script gửi tối đa 10 tin, cách nhau 180 giây theo mặc định; đồng thời thăm dò Telegram để nhận `/stop` trong thời gian chờ.
- `~/.config/telegram/config.json`: cấu hình bot dùng chung trong vùng riêng của Termux. Các script Telegram khác có thể dùng chung file này.
- `market_price_bot/`: ứng dụng riêng lấy giá vàng/Bitcoin mỗi 5 phút, lưu lịch sử SQLite và trả lời `/gold-price`, `/bitcoin-price`. Xem [README của dự án](market_price_bot/README.md) để cài đặt và vận hành.
- `camera_bot/`: bot Telegram Python cho Termux, chụp ảnh bằng `/photo-front` hoặc `/photo-back` (lệnh `/photo` giữ camera sau) và dừng bằng `/stop`. Quay video chưa được hỗ trợ do Termux:API hiện không có lệnh ghi video. Xem [README của dự án](camera_bot/README.md).

Script dùng thư viện chuẩn Python (`urllib`), không cần cài thêm package. Python 3.14.6 đã được xác nhận hoạt động trong Termux.

## Thiết bị đã thử

- Samsung SM-J400F
- Android 10
- Termux cài từ F-Droid
- ADB nhận thiết bị ở trạng thái `device`

## Cài đặt ban đầu

Cài Termux từ F-Droid hoặc GitHub Releases chính thức. Không trộn Termux và plugin lấy từ các nguồn ký APK khác nhau. Mở Termux và cài Python:

```sh
pkg update && pkg upgrade -y
pkg install python -y
python --version
```

Cấp quyền truy cập bộ nhớ chia sẻ để Termux có thể đọc file script được ADB chép vào Download:

```sh
termux-setup-storage
```

Chấp thuận hộp thoại Android nếu được hỏi. Khi đó thư mục Download dùng trong Termux là `~/storage/downloads`.

## Kết nối ADB và chép script

Bật USB debugging trên điện thoại, kết nối cáp USB và chấp thuận hộp thoại ủy quyền RSA trên điện thoại. Từ thư mục repo trên Windows, kiểm tra kết nối:

```sh
adb devices -l
```

Chép script vào Download:

```sh
adb push telegram_test.py /sdcard/Download/telegram_test.py
```

Trong Git Bash, nếu đường dẫn Android `/sdcard/...` bị MSYS chuyển thành đường dẫn Windows, chạy:

```sh
MSYS_NO_PATHCONV=1 adb push telegram_test.py /sdcard/Download/telegram_test.py
```

Có thể mở Termux bằng ADB nếu cần:

```sh
adb shell am start -n com.termux/.app.TermuxActivity
```

## Cấu hình Telegram

Mở bot trong Telegram và gửi `/start` trước để bot được phép nhắn tin riêng. Mặc định, script dùng chat ID admin hiện có trong mã nguồn thử nghiệm. Có thể thay đổi giá trị `DEFAULT_CHAT_ID` trong `telegram_test.py` nếu thử với chat khác.

Lần chạy đầu tiên, nếu không có cấu hình sẵn, script hỏi bot token bằng prompt ẩn rồi lưu cấu hình vào:

```text
~/.config/telegram/config.json
```

Schema của file:

```json
{
  "bot_token": "TOKEN_MOI_CUA_BOT",
  "chat_id": "CHAT_ID_CUA_BAN"
}
```

File được tạo với quyền `600` trong home riêng của Termux. Không đặt file chứa token trong Download, không commit token, không đưa token vào lệnh `adb shell input text`, và không gửi token vào chat.

Nếu đã có file cấu hình cũ ở `~/.config/telegram-test/config.json`, script tự chuyển file đó sang vị trí mới khi file mới chưa tồn tại. Nếu cần thay token sau này, mở file bằng editor ngay trong Termux, sửa `bot_token`, rồi kiểm tra quyền:

```sh
nano ~/.config/telegram/config.json
chmod 600 ~/.config/telegram/config.json
```

Biến môi trường `TG_BOT_TOKEN` và `TG_CHAT_ID`, nếu được đặt trong Termux, sẽ ghi đè các giá trị tương ứng trong JSON cho tiến trình hiện tại; script không lưu lại các giá trị ghi đè này.

## Chạy bài thử gửi tin

Trong Termux:

```sh
python ~/storage/downloads/telegram_test.py --count 10 --interval 180
```

Hoặc gửi câu lệnh vào terminal Termux đang mở qua ADB:

```sh
adb shell input text 'python%s/sdcard/Download/telegram_test.py%s--count%s10%s--interval%s180'
adb shell input keyevent 66
```

Lệnh ADB giả lập gõ bàn phím vào giao diện hiện tại; bảo đảm Termux đang mở và terminal đang nhận input. Không dùng cách này để nhập token. Token chỉ nên nhập trực tiếp ở prompt ẩn trên điện thoại.

Hành vi hiện tại:

1. Script đọc config JSON, hoặc hỏi token ẩn nếu chưa có.
2. Gọi Telegram `getUpdates` để bỏ qua các update cũ và thiết lập offset.
3. Gửi tin đầu tiên ngay lập tức.
4. Chờ theo khoảng thời gian đã chọn, đồng thời long-poll `getUpdates` tối đa 20 giây mỗi vòng.
5. Nếu nhận `/stop` từ đúng sender ID và chat ID đã cấu hình, gửi xác nhận và kết thúc.
6. Nếu lần gửi tin gặp lỗi, dừng thay vì lặp gửi ở các chu kỳ sau.

Lệnh `/srtop` không được hỗ trợ; chỉ dùng `/stop`. Trong khoảng polling, độ trễ nhận lệnh thông thường tối đa khoảng 20 giây, ngoài ảnh hưởng mạng/Android.

## Dừng và theo dõi

Cách ưu tiên là gửi `/stop` trong chat riêng với bot. Script chỉ kiểm tra lệnh này trong lúc chờ giữa hai lần gửi; lần gửi đầu tiên xảy ra ngay khi khởi chạy.

Có thể xem tiến trình từ máy tính:

```sh
adb shell ps -A | grep '[p]ython'
```

ADB shell thường không có quyền gửi tín hiệu trực tiếp tới tiến trình thuộc Termux. Nếu không thể dừng bằng Telegram, force-stop toàn bộ Termux:

```sh
adb shell am force-stop com.termux
```

Force-stop đóng mọi phiên Termux đang mở và kết thúc các tiến trình của Termux. Mở lại Termux để tiếp tục sử dụng.

Ctrl+C trên terminal máy tính không gửi tín hiệu ngắt tới chương trình đang chạy trong terminal điện thoại. Khi thao tác trực tiếp trong Termux, Ctrl+C trên bàn phím Termux có thể ngắt tiến trình foreground.

## Chạy nền và màn hình khóa

Trong lượt thử này, người dùng xác nhận script đã tiếp tục hoạt động và gửi tin khi điện thoại khóa màn hình. Đây là kết quả trên thiết bị cụ thể, không phải cam kết cho mọi phiên bản Android hoặc mọi thiết lập pin.

Nếu cần tăng độ ổn định trên Samsung, kiểm tra mục quản lý pin và đặt Termux vào danh sách không ngủ/tối ưu pin nếu thiết bị cung cấp lựa chọn đó. Wake lock có thể giữ CPU thức nhưng làm hao pin; chỉ thử khi cần và so sánh mức tiêu thụ. Không force-stop Termux trong khi bài thử chạy.

## Kết quả phiên thử

- ADB nhận Samsung SM-J400F chạy Android 10; Termux đã cài.
- Python 3.14.6 hoạt động.
- Script gửi thành công ít nhất hai tin trong lượt thử ban đầu.
- Người dùng đã khóa màn hình và xác nhận script vẫn gửi được khi chạy nền.
- `/stop` được nhận; sau đó ADB không còn thấy tiến trình Python.
- Script hiện đã được cập nhật để chỉ nhận `/stop` và lưu cấu hình dùng chung dưới `~/.config/telegram/config.json`.

## Tiến độ ứng dụng giá

- `market_price_bot/` đã được tạo, kiểm thử offline và chép sang `~/storage/downloads/market_price_bot` trên Termux.
- Ngày 2026-09-27, chạy `python -m market_price_bot` từ `~/storage/downloads`. Log Termux xác nhận đã lưu mẫu XAU và Bitcoin vào SQLite; bot khởi động thành công và người dùng xác nhận nhận được giá qua Telegram.
- 13 kiểm thử `unittest` chạy thành công trên máy phát triển, gồm ghi/đọc/mở lại SQLite, xử lý lệnh, xác thực người gửi và cô lập lỗi nguồn.
- Chưa xác minh trên điện thoại: nhiều chu kỳ 5 phút, tiếp tục khi khóa màn hình, dữ liệu còn sau khi dừng/khởi động lại, và `/stop`/từ chối người gửi không được phép trong phiên chạy thực tế.

## Giới hạn và lưu ý API

- Telegram Bot API sử dụng `getUpdates` cho polling. Mỗi bot chỉ nên có một consumer polling đang hoạt động; tắt bot PC trong khi script Android nhận update. Nếu bật hai consumer cùng lúc, chúng có thể tranh nhau lấy update hoặc gặp lỗi xung đột.
- Ứng dụng giá hiện hỗ trợ `/gold-price`, `/bitcoin-price` và `/stop`; `/test` và `/task` chưa được triển khai. Không gửi lệnh shell tùy ý từ Telegram. Nếu bổ sung tác vụ sau này, cần allowlist, giới hạn thời gian và kiểm tra quyền admin.
- Chỉ khi mô hình nhận lệnh được kiểm tra an toàn mới nối với tác vụ thật.
- Có thể gọi API bên thứ ba (ví dụ Binance) bằng HTTPS từ Termux. Bắt đầu bằng endpoint dữ liệu công khai hoặc testnet; không bật giao dịch thật hay quyền rút tiền trong thử nghiệm nền này.
- Script kiểm tra khả năng chạy tác vụ, không tự chứng minh Android tiết kiệm điện hơn PC. Muốn kết luận điện năng cần phép đo riêng; USB dùng cho ADB cũng thường cấp nguồn cho điện thoại.

## Bảo mật token

Bot token đã xuất hiện trực tiếp trong mã nguồn/tệp đính kèm của cuộc trao đổi. Hãy xem token đó là đã lộ: thu hồi bằng BotFather, tạo token mới và thay ở các nơi cần dùng trước khi tiếp tục. Cấu hình Termux và cấu hình bot PC độc lập nhau.

Trong dự án PC, `bot.py` có giá trị token mặc định trong mã và hàm khởi tạo có thể nạp `config.json` của dự án để ghi đè. Hãy chuyển bot PC sang đọc secret từ cấu hình riêng hoặc biến môi trường và xóa token đã lộ khỏi mã. Không đưa credential vào tài liệu, log, commit hoặc ảnh chụp màn hình.
