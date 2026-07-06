# BẢN GIẢI THÍCH DỄ HIỂU
### Đọc kèm với "Kế hoạch triển khai phần mềm"

> Bản này nói cùng một nội dung với bản kế hoạch chính thức, nhưng bằng ngôn ngữ đời thường.
> Mục tiêu: đọc xong là **hiểu bức tranh tổng thể** và **tự tin trả lời hội đồng**, không cần biết lập trình.

---

## 1. Hệ thống này thực ra làm gì? (Một câu)

Bình thường khi đạp xe tập, muốn nặng hơn hay nhẹ hơn thì bạn phải **tự vặn núm chỉnh tải**. Đồ án của Nhật thay việc đó bằng một hệ **tự động**: máy đo nhịp tim của bạn liên tục, rồi **tự tăng/giảm độ nặng** để giữ nhịp tim ở đúng vùng tập luyện an toàn (60–80% mức dự trữ nhịp tim), suốt buổi 30 phút.

Giống như **ga tự động (cruise control) trên ô tô**: bạn đặt tốc độ mong muốn, xe tự nhấn ga/nhả ga để giữ tốc độ đó. Ở đây "tốc độ" là **nhịp tim**, và "chân ga" là **độ nặng của bàn đạp**.

---

## 2. Bốn nhân vật trong câu chuyện

Hãy hình dung hệ thống như một dây chuyền có 4 nhân vật, chuyền tín hiệu cho nhau thành một vòng tròn khép kín:

**① Máy đo tim (BIOPAC MP36)** — dán điện cực lên người, đọc tín hiệu điện tim (ECG) rất nhanh (1000 lần/giây). Đây là "đôi tai" nghe nhịp tim.

**② Máy tính (phần mềm Python)** — bộ não. Nó nhận tín hiệu tim thô, **đếm ra nhịp tim** (thuật toán Pan-Tompkins tìm từng nhịp đập), rồi **quyết định** nên cho bàn đạp nặng lên hay nhẹ đi (đây là chỗ dùng **Fuzzy Logic** — sẽ giải thích ở Mục 4).

**③ Arduino (mạch điều khiển nhỏ)** — cánh tay. Nó nhận lệnh "đặt độ nặng mức số mấy" và **điều khiển mô-tơ** xoay cụm phanh nam châm tới đúng vị trí.

**④ Xe đạp GENUS-249** — cơ thể. Cụm phanh nam châm tạo ra lực cản (16 mức, từ nhẹ tới nặng).

Rồi vòng lặp lại: độ nặng thay đổi → người đạp mệt hơn/đỡ hơn → **nhịp tim thay đổi** → máy đo tim đọc lại → não quyết định lại... cứ thế mỗi 5–8 giây một lần. **Đó là "vòng điều khiển kín".**

---

## 3. Điểm quan trọng nhất về Arduino (dễ hiểu sai)

Đây là chỗ mà lúc đầu bản kế hoạch đã hiểu sai, và Nhật đã sửa lại. Cần nắm thật rõ vì hội đồng có thể hỏi:

**Arduino là một bộ não độc lập, tự sống, KHÔNG cần máy tính.**

Nghĩ thế này: Nhật đã **nạp sẵn một chương trình vĩnh viễn** vào Arduino (thay cho mạch zin của hãng). Chương trình này tự nó đã đủ để chiếc xe hoạt động hoàn chỉnh — có **nút bấm vật lý tăng/giảm độ nặng**, y như chiếc xe hãng bình thường. Rút dây USB ra, tắt máy tính đi, **xe vẫn chạy ngon lành**, người dùng vẫn bấm nút chỉnh tải được.

Vậy máy tính (Python) đóng vai gì? Nó chỉ là một **"người điều khiển từ xa" cắm thêm vào**. Khi cắm USB, máy tính có thể **gọi đúng lệnh** để đặt độ nặng chính xác theo nhịp tim. Nhưng nó **không phải là thứ làm cho xe hoạt động** — xe vốn đã tự hoạt động rồi.

> **Câu trả lời gọn nếu hội đồng hỏi "nếu máy tính treo/rớt kết nối thì sao?":**
> *"Không sao cả. Firmware Arduino chạy độc lập, thiết bị tiếp tục hoạt động bình thường và người dùng vẫn chỉnh tải bằng nút bấm vật lý. Máy tính chỉ là lớp điều khiển tự động thêm vào, không phải điều kiện để thiết bị vận hành. Đây chính là lớp an toàn phần cứng độc lập với phần mềm."*

**Hệ quả kỹ thuật (một điểm tinh tế nhưng quan trọng):** vì người dùng có thể bấm nút chỉnh tay **bất cứ lúc nào** — kể cả giữa lúc máy tính đang tự điều khiển — nên phần mềm **không được đoán mò** độ nặng hiện tại. Trước mỗi lần tính toán, nó phải **hỏi lại Arduino** "hiện đang ở mức mấy?" và tin vào câu trả lời đó. Nếu thấy khác với dự đoán (do có người bấm nút), nó ghi nhận "à, có người chỉnh tay" rồi **tính tiếp từ con số thực tế**, không cãi nhau với người dùng. Giống như cruise control: nếu bạn tự đạp phanh, xe không "giành lại" mà nhường bạn, rồi mới tính tiếp.

---

## 4. Fuzzy Logic là gì, và tại sao dùng nó?

### Fuzzy Logic nói nôm na

Máy tính bình thường suy nghĩ kiểu **đen/trắng**: nhịp tim hoặc "cao" hoặc "thấp", không có ở giữa. Nhưng con người suy nghĩ kiểu **mờ (fuzzy)**: "hơi cao một chút", "thấp kha khá", "gần đạt rồi".

Fuzzy Logic cho phép máy tính suy nghĩ **giống người** — bằng các luật dạng câu chữ:
- *"Nếu nhịp tim **thấp hơn nhiều** so với mục tiêu VÀ **đang không tăng** thì **tăng độ nặng nhiều**."*
- *"Nếu nhịp tim **đã đúng vùng** thì **giữ nguyên**."*
- *"Nếu nhịp tim **cao hơn** VÀ **đang tăng tiếp** thì **giảm độ nặng nhiều**."*

Hệ thống của Nhật có **15 luật** như vậy, dựa trên 2 điều nó quan sát:
1. **Nhịp tim đang lệch bao nhiêu** so với mục tiêu (thấp/cao, ít/nhiều).
2. **Nhịp tim đang đi theo hướng nào** (đang tăng, đang giảm, hay ổn định) — để **đoán trước**, tránh chỉnh quá tay.

Điểm thứ 2 giống như lái xe giỏi: bạn không đợi tới lúc sát đuôi xe trước mới phanh, mà thấy nó **đang chậm lại** là nhả ga sớm. Fuzzy cũng vậy — thấy nhịp tim **đang tăng nhanh** thì nới độ nặng sớm, không đợi vượt ngưỡng.

### Tại sao Fuzzy mà không phải công thức toán thông thường (PID)?

PID là cách điều khiển kinh điển, nhưng nó cần 3 thứ mà **cơ thể người không có**:
1. Một công thức cố định biến "độ nặng → nhịp tim" — nhưng mỗi người phản ứng mỗi khác, và cùng một người lúc khỏe lúc mệt cũng khác.
2. Bộ tham số tối ưu dùng chung cho mọi người — không tồn tại.
3. Đầu ra liên tục — nhưng ở đây tải chỉ có **16 nấc rời rạc**, không mượt.

Fuzzy hợp hơn vì nó **không cần công thức chính xác** — nó điều khiển bằng **kinh nghiệm dạng luật**, giống cách một huấn luyện viên chỉnh tải bằng cảm nhận. Đây là lý lẽ chính đáng để bảo vệ trước hội đồng.

### Vì sao chọn "tự viết" thay vì dùng thư viện có sẵn?

Có 3 lựa chọn: tự viết bằng công cụ tính toán cơ bản (numpy), hoặc dùng 1 trong 2 thư viện có sẵn (`scikit-fuzzy`, `simpful`).

**Quyết định: tự viết.** Lý do quan trọng nhất là **an toàn khi đóng gói và chạy thật**:

- Khi biến phần mềm thành file `.exe` để chạy trên máy phòng lab, thư viện càng nhiều thì càng dễ **thiếu linh kiện lúc chạy trên máy lạ** (điều Nhật đã từng gặp). `scikit-fuzzy` kéo theo cả một thư viện phụ nặng nề (`networkx`) — thêm một chỗ có thể vỡ **ngay giữa buổi bảo vệ**.
- Tự viết thì mọi công thức **nằm trong tay mình**, các chốt an toàn (vùng chết, giới hạn 1–16) gắn liền ngay trong code, và **kiểm tra được từng luật một** để chứng minh với hội đồng "đầu ra đúng như thiết kế".
- Bài toán này **quá nhỏ** (chỉ 15 luật) để một thư viện đồ sộ mang lại lợi ích thật.

> **Mẹo ăn điểm:** vẫn dựng lại đúng bộ luật này **một lần** bằng thư viện `simpful` (nhẹ, đã được công bố khoa học), so kết quả với bản tự viết. Nếu hai bên ra số giống nhau → trong báo cáo ghi *"đã kiểm chứng chéo với thư viện đã qua bình duyệt khoa học"*. Vừa chắc chắn đúng, vừa không phải gánh rủi ro thư viện lúc chạy thật.

---

## 5. Buổi tập 30 phút diễn ra thế nào? (3 pha)

Phần mềm chia buổi tập thành 3 giai đoạn, **canh theo đồng hồ tuyệt đối** (không đếm số lần tính — vì mỗi lần tính cách nhau 5–8 giây, đếm sẽ sai lệch dần):

**① Khởi động (0–5 phút):** đặt độ nặng ở **mức cố định** tùy theo người này năng động hay ít vận động (phân loại bằng bộ câu hỏi IPAQ). Chưa dùng Fuzzy — vì lúc mới bắt đầu nhịp tim còn "loạng choạng", chưa ổn định để điều khiển tinh vi.

**② Chính (5–25 phút):** đây là **sân khấu của Fuzzy**. Cứ mỗi 5–8 giây, hệ tính lại và chỉnh độ nặng để giữ nhịp tim trong vùng mục tiêu. Đây là 20 phút "làm việc thật" của đồ án.

**③ Hạ nhiệt (25–30 phút):** giảm độ nặng **đều đặn tuyến tính** về mức nhẹ nhất. Cố ý **không dùng Fuzzy** ở đây, vì cần đo một chỉ số sinh lý quan trọng: **nhịp tim hồi phục** (tim chậm lại bao nhiêu sau 1 phút ngừng gắng sức — gọi là HRR1). Nếu Fuzzy vẫn can thiệp thì phép đo này bị nhiễu.

> **Lưu ý thuật ngữ dễ bị hỏi:** có **hai** thứ viết tắt gần giống nhau, đừng lẫn:
> - **HRR** = Heart Rate *Reserve* (dự trữ nhịp tim) — dùng để **tính vùng mục tiêu** lúc đầu.
> - **HRR1 / HR_recovery** = Heart Rate *Recovery* (hồi phục nhịp tim) — đo **sau khi tập** ở pha hạ nhiệt.
> Trong code và báo cáo phải gọi tên khác nhau rõ ràng.

---

## 6. Làm phần mềm theo thứ tự nào? (Chiến lược thông minh)

Có một mẹo tổ chức công việc rất hay trong kế hoạch: **tách phần cần phần cứng ra khỏi phần không cần**.

Nhóm đã làm một "**Arduino giả lập**" (Mock) — một đoạn code giả vờ là Arduino, trả về nhịp tim giả dao động quanh vùng mục tiêu. Nhờ nó, **toàn bộ bộ não phần mềm có thể viết và thử nghiệm xong xuôi mà chưa cần đụng tới xe đạp thật.**

Nên thứ tự là:
1. Viết **bộ Fuzzy** (M1) — bộ ra quyết định.
2. Viết **bộ ghi nhật ký** (M3) — lưu lại buổi tập.
3. Viết **nhạc trưởng** (M2) — thứ điều phối 3 pha, gọi Fuzzy, ra lệnh.
4. Viết **màn hình theo dõi** (M4) — hiển thị nhịp tim/độ nặng/thời gian.
5. **Nối tất cả lại** (M9).

Xong 5 bước này là **phần mềm đã chạy trọn vẹn một buổi tập giả lập từ đầu tới cuối** — đủ để bảo vệ được logic điều khiển, **kể cả khi phần cứng chưa sẵn sàng**. Sau đó mới làm firmware Arduino thật (M7) và ghép vào (chỉ cần **đổi 1 dòng** để chuyển từ Arduino-giả sang Arduino-thật).

Cách này giảm rủi ro rất nhiều: nếu sát ngày mà phần cứng trục trặc, ít nhất phần mềm vẫn demo được đầy đủ.

---

## 7. An toàn — điều hội đồng chắc chắn quan tâm

Vì hệ thống gắn với nhịp tim người thật, an toàn là số một. Có **nhiều lớp bảo vệ chồng lên nhau**:

- **Lớp cứng nhất (phần cứng):** nút bấm vật lý luôn hoạt động, ai cũng chỉnh tay được bất cứ lúc nào — **không phụ thuộc máy tính**. Đây mới là "phanh tay" thật sự của hệ thống.
- **Nếu tuột điện cực / mất tín hiệu tim ngắn:** phần mềm **giữ nguyên độ nặng**, không hành động dựa trên dữ liệu cũ, và cảnh báo.
- **Nếu mất tín hiệu lâu:** phần mềm chủ động **giảm về mức nhẹ nhất** cho an toàn.
- **Nút STOP trên màn hình:** bấm là về mức nhẹ nhất và kết thúc buổi tập.
- **Giới hạn cứng:** độ nặng không bao giờ vượt ra ngoài 1–16, dù tính toán có ra số lạ.

> **Nguyên tắc vàng:** bất cứ khi nào phần mềm không chắc chắn, nó **lùi về mức nhẹ nhất** — thà nhẹ quá còn hơn nặng quá. Và trên hết, **nút bấm tay luôn là chốt an toàn cuối cùng**.

---

## 8. Ranh giới đồ án — đừng hứa quá lời

Một điểm khôn ngoan cần nhớ khi trình bày: hệ thống này chứng minh được là nó **giữ được nhịp tim trong vùng mục tiêu** trong buổi tập. Nó **KHÔNG** chứng minh "cải thiện sức khỏe tim mạch lâu dài" — muốn chứng minh điều đó cần thí nghiệm nhiều tuần trên nhiều người, vượt xa phạm vi một đồ án tốt nghiệp.

Nói đúng phạm vi = tránh bị hội đồng "bắt bẻ hứa hẹn quá mức". Đây là điểm cộng về sự cẩn trọng khoa học.

---

## Tóm lại trong 5 ý

1. **Cruise control cho nhịp tim:** đo tim → tự chỉnh độ nặng → giữ nhịp tim đúng vùng.
2. **Arduino tự sống độc lập**, có nút bấm tay; máy tính chỉ là điều khiển từ xa cắm thêm vào.
3. **Fuzzy Logic** = cho máy suy nghĩ kiểu người ("hơi cao thì giảm nhẹ"), hợp hơn công thức cứng vì cơ thể mỗi người mỗi khác. Tự viết để an toàn khi chạy thật.
4. **3 pha:** khởi động (mức cố định) → chính (Fuzzy) → hạ nhiệt (để đo hồi phục tim).
5. **Làm phần mềm trước với Arduino-giả**, xong mới ghép phần cứng thật — giảm rủi ro sát ngày bảo vệ.
