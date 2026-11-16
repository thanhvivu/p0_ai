# Phân tích chương trình JAKA `jamaguchi` – mở rộng cho CNC3..CNC6

Các file trong thư mục này:

| File | Nội dung |
|---|---|
| `jamaguchi_goc.txt` | Code gốc (đang chạy CNC1/CNC2) – giữ để so sánh |
| `jamaguchi_cnc36.txt` | Bản bổ sung cho CNC3..CNC6. Tìm chuỗi `[CNC36]` để thấy mọi chỗ sửa |
| `PHAN_TICH.md` | Tài liệu này |

Số dòng trong mục 1–3 là số dòng của **code gốc**.

---

## 1. Ngôn ngữ và quy ước

* Ngôn ngữ script của JAKA: `if(...):` … `else:` … `end`, `while(...):` … `end`. **Khối được đóng bằng `end`, thụt lề không có ý nghĩa** (vì vậy code gốc thụt lề lộn xộn mà vẫn chạy).
* IO đi qua Modbus kiểu `4`. Chỉ số = số thứ tự − 1: `DI35` → `get_digital_input(4,34)`, `DO35` → `set_digital_output(4,34,…)`.
* Bộ điều khiển **không nhận phép tính trong lệnh gán** (ví dụ `a = b + 1`) nhưng **nhận phép tính trong điều kiện `if`** (đoạn kiểm tra vùng nguy hiểm và TCP ±20 mm đã dùng như vậy).
* Code gốc cố ý **không truyền biến làm chỉ số IO** cho `get_digital_input` (một số firmware đọc sai). Bản bổ sung giữ nguyên quy tắc này.

## 2. Cấu trúc tổng thể của code gốc

```
1–58      Header, mô tả IO, biến trạng thái (active_process, active_case, at_* ...)
60–71     Tốc độ + offset User-frame cho CNC1/CNC2
73–191    Điểm dạy (joint): P1, P6, door C1/C2, air, CNC1, CNC2, P5, P7, P8
          + mảng min/max (±5°) dùng cho nhận diện vị trí khi Home
193–266   Reset toàn bộ DO/AO khi chạy chương trình
268       while(1):  ← vòng quét chính, mỗi vòng sleep(0.1)
 ├ 271–303    Đọc AI3 → chọn bộ tốc độ
 ├ 305–440    DI16 = thoát Process (về Door, P2/P3/P4 dừng ở Door, không về Home)
 ├ 441–1425   DI90 = Home Process (khôi phục an toàn từ vị trí bất kỳ)
 │    ├ 496–527   AI16 (số CNC) → cửa C1 (CNC lẻ) hoặc C2 (CNC chẵn)
 │    ├ 533–641   Vùng nguy hiểm CNC1/CNC2 (tính theo TCP, user frame usrfr_thanh)
 │    ├ 643–1097  So vị trí thực với từng điểm dạy → home_match_code 1..19
 │    └ 1163–1415 Lộ trình thoát: lùi theo đúng đường → Door → HomeLocation → DO16
 ├ 1427–1639  Chọn Process (ưu tiên P1→P10) theo DI18..DI27, bật AO2 + DO18..27
 │            P2/P3/P4: chờ DI83 (Door1) / DI84 (Door2) → MoveJ tới Door
 └ 1641–2782  Đang trong Process
      ├ DI16 → thoát Process;  DI17 → xóa Case, quay lại quét Case
      ├ 1770–1912  Chọn Case theo DI28, DI30..33, DI35..38, DI40..43, ...
      └ 1914–2773  Thực thi Case
           ├ 1918–1951  ánh xạ P3/P4 → cnc_motion_case 29..32   ← ĐIỂM MẤU CHỐT
           ├ 1982–2337  Chuyển động CNC dùng chung (29=Load lẻ, 30=Unload lẻ,
           │            31=Load chẵn, 32=Unload chẵn)
           ├ 2344–2695  P5 (Clean), P6 (Bavia), P7 (Inspection), P8 (Change tool)
           └ 2700–2773  Case xong → bật DO "Case Comp", giữ đến khi PLC bật DI17
```

### Trình tự bắt tay với PLC cho 1 Case CNC (ví dụ P3 – Load CNC3)

1. PLC đưa trục Axis1 (`TFRobot`) tới vị trí `Pos CNC34`, rồi bật **DI20** (P3_Condition).
2. Robot: `AO2 = 3`, bật **DO20** (P3_Interlock), chờ **DI83/DI84** chọn cửa → MoveJ tới Door.
3. PLC bật **DI35** (P3_Case1 Load CNC3) → robot chạy `cnc_motion_case = 29`:
   AirV1 + DO74/DI74 → AirSwitchTool + DO75/DI75 → LoadWait → Load + DO61/DI61 →
   LoadEnd + **DO79/DI79 (kẹp chuck)** → lùi về Load → LoadWait.
4. Robot bật **DO35** (Case Comp), giữ cho tới khi PLC bật **DI17**, rồi chờ DI17 tắt.
5. PLC có thể gọi Case khác (DI36..38) hoặc bật **DI16** để thoát → robot về Door, bật DO17.

## 3. Phát hiện quan trọng: P3/P4 *đã có sẵn khung*

Code gốc **đã** chọn P3/P4, đã đọc DI35..38/DI40..43, đã bật DO35..38/DO40..43 và
đã ánh xạ chúng vào đúng chuyển động của CNC1/CNC2 (dòng 1922–1951,
log `"P3 USE SHARED CNC MOTION CASE1-4"`).

Lý do: base robot nằm trên trục Axis1. Nếu PLC dừng trục ở vị trí sao cho CNC3/CNC4
(và CNC5/CNC6) có **cùng vị trí tương đối với base** như CNC1/CNC2, thì các điểm joint
giống hệt nhau. Thực tế khó đạt độ chính xác đó (sai số lắp đặt máy, sai số dừng trục,
chiều cao chuck), nên điểm vẫn phải dạy riêng cho từng máy.

Những thứ còn thiếu cho CNC3..CNC6:

| # | Thiếu | Ảnh hưởng |
|---|---|---|
| 1 | Bộ điểm dạy riêng cho CNC3..CNC6 (Load/Unload/Wait/End/Down) | Lệch vài mm là đâm vào chuck |
| 2 | Điểm thổi khí (AirC1v1, AirSwitchTool, AirC2v1, AirC2) nằm ở từng máy CNC | Cũng phải theo từng máy |
| 3 | Home (DI90) chỉ so sánh với điểm CNC1/CNC2 và lùi theo điểm CNC1/CNC2 | Khi đang ở CNC3..6 mà bấm Home, robot có thể MoveL tới điểm của CNC1 |
| 4 | Tín hiệu kẹp chuck: map chỉ có **DO79/DI79 = chuck CNC1**, **DO78/DI78 = chuck CNC2** | Phía PLC phải định tuyến theo AO2 (process) cho CNC3..6, hoặc cần thêm tín hiệu |
| 5 | Không có kiểm tra trục Axis1 đã đúng vị trí cặp máy | Nếu PLC gửi sai, robot đi vào sai máy |

## 4. Đánh giá bản của Gemini (`jamaguchi_updated.txt`)

**Ý tưởng đúng:** tạo bộ điểm "active" `p_odd_*` (CNC lẻ) và `p_even_*` (CNC chẵn),
gán lại theo P2/P3/P4, và sửa phần chuyển động 29..32 để dùng bộ active. Đây là cách sửa
ít nhất và đúng hướng. Phần chuyển động Case đã được thay đầy đủ.

**Các lỗi / thiếu sót:**

1. Đổi giá trị 3 điểm CNC2 (`p_load_m2_wait`, `p_load_c2`, `p_end_load_m2v1`).
   **Đã xác nhận: đây là điểm CNC2 vừa teach lại** → bản bổ sung đã cập nhật theo giá trị này.
   Nhưng Gemini lại chép giá trị CNC2 *cũ* sang CNC4/CNC6; bản bổ sung chép giá trị *mới*.
2. Vì đổi điểm CNC2 mà **không cập nhật mảng min/max**, J4 của cả 3 điểm mới
   (162.6–162.9°) **nằm ngoài khoảng ±5°** (165.8–176.0°). Khi bấm Home lúc robot đang ở
   LoadWait/LoadC2/EndLoadM2v1 của CNC2, robot không nhận ra điểm và chuyển sang nhánh
   "vùng nguy hiểm" (MoveL thẳng ra DoorC2) hoặc AI16. Nhánh này kém an toàn hơn lộ trình lùi theo điểm.
3. Điểm CNC3..CNC6 chỉ là **bản sao** của CNC1/CNC2 nhưng comment lại ghi "TAUGHT POINTS",
   dễ khiến người sau tưởng là đã dạy.
4. **Không chuyển điểm thổi khí** (AirC1v1, AirSwitchTool, AirC2v1, AirC2) theo từng máy.
5. **Không sửa phần Home DI90**: vẫn nhận diện và lùi theo điểm CNC1/CNC2.
6. Không động tới tín hiệu kẹp chuck DO78/DO79 (không có chú thích cảnh báo).
7. Có 1 ký tự TAB ở dòng 1979. Không gây lỗi cú pháp vì JAKA dùng `end`, nhưng nên bỏ.

## 5. Bản bổ sung `jamaguchi_cnc36.txt` (dựa trên **code gốc**, không dựa trên bản Gemini)

Mọi chỗ sửa đều có nhãn `[CNC36]`.

1. **Giữ điểm CNC1 của code gốc; cập nhật 3 điểm CNC2 vừa teach lại**
   (`p_load_m2_wait`, `p_load_c2`, `p_end_load_m2v1`).
2. **Thêm offset** `p_c3..p_c6_user_x_offset` (tinh chỉnh giống CNC1/CNC2).
3. **Thêm bộ điểm CNC3..CNC6** gồm điểm thổi khí và **điểm cửa `p_door_c3..p_door_c6`**.
   Hiện là **PLACEHOLDER**: CNC3/CNC5 = bản sao CNC1, CNC4/CNC6 = bản sao CNC2 (bản CNC2 mới).
   Mỗi điểm có dòng ghi chú nguồn ngay phía trên.
4. **Biến `cnc_pair`** (1 = CNC1/2, 2 = CNC3/4, 3 = CNC5/6) và khối gán bộ điểm active
   `p_odd_*`/`p_even_*` (19 biến: cửa, offset, điểm thổi khí, Load/Unload).
   * Khi vào Process (trước khi MoveJ tới cửa): P2 → 1, P3 → 2, P4 → 3, rồi gán bộ điểm.
     Nhờ vậy cửa lúc vào và lúc thoát DI16 là cửa của đúng cặp máy.
   * Khi thực thi Case: gán lại lần nữa (an toàn khi nạp lại chương trình giữa chừng).
   * Khi Home DI90: chọn `cnc_pair` theo **AI16** (1–2 / 3–4 / 5–6). Nếu AI16 không hợp lệ thì giữ cặp của Case gần nhất.
5. **Chuyển động Case 29..32**: dùng `p_odd_*`/`p_even_*` cho mọi điểm, kể cả điểm thổi khí.
6. **Home DI90**: nhận diện và lùi theo bộ điểm active. Phép kiểm tra joint ±5° nay
   **tính trực tiếp từ điểm dạy** (`home_match_joint[i] ± 5.0` trong `if`), không dùng
   các mảng `*_min/*_max` cố định nữa. Nhờ vậy khi dạy lại điểm (hoặc thêm CNC3..6) thì không phải
   tự tính lại 2 mảng cho mỗi điểm. Code gốc vốn đã có lỗi tương tự: mảng min/max của `p_c1_load*` lệch khoảng 0,2–0,5° so với điểm hiện tại.
   Các mảng cũ vẫn được khai báo nhưng không còn dùng.
7. **Cảnh báo AI16** (chỉ ghi log, không chặn): khi chạy Case, nếu AI16 không thuộc cặp
   máy của Process hiện tại thì log `WARNING AI16 ... CHECK AXIS1 POSITION`.
8. **Chú thích tại DO79/DI79 và DO78/DI78** về việc PLC phải định tuyến tín hiệu kẹp chuck cho CNC3..6.

9. **Cửa theo cặp máy**: lúc vào Process, lúc thoát DI16, và trong Home (nhận diện điểm cửa
   + các lệnh đi về cửa "giữ J6 hiện tại") đều dùng `p_odd_door`/`p_even_door`.
   Trong Home, J1..J5 của cửa trước đây là số viết cứng (`-126.687`, `82.806`...) nay đọc từ
   `p_odd_door[i]` / `p_even_door[i]`. **Code gốc chưa từng dùng phép gán dạng `a[i] = b[i]`**,
   nên đã test riêng trên bộ điều khiển Zu ở chế độ Simulation (2026-11-17): log T2..T7 đều OK —
   gán phần tử từ mảng khác chép đúng giá trị, phép tính trong `if` đúng, gán nguyên mảng đúng.
   Vẫn nên chạy thử DI90 một lần ở tốc độ thấp trên robot thật (firmware thật có thể khác bản mô phỏng).

Không thay đổi: P1, P5–P8, logic DI16/DI17, chọn Process, chọn cửa DI83/DI84,
trình tự chuyển động (đã xác nhận cặp 3/4, 5/6 chạy cùng kiểu với cặp 1/2),
vùng nguy hiểm theo TCP (ranh giới X vẫn lấy theo DoorC1/DoorC2; tính theo base robot nên dùng
chung được khi các cặp máy bố trí giống nhau — nếu cửa CNC3..6 sau khi teach lệch nhiều, cần đo lại),
`p_end_load_m2v2`, hành vi P2/P3/P4 thoát ở cửa không về Home.

> Lưu ý: tôi đã kiểm tra cân bằng `if/while … end` và rà toàn bộ diff,
> nhưng **chưa chạy trên bộ điều khiển JAKA thật**. Phải nạp thử và test theo mục 7.

## 6. Việc cần làm phía PLC / cần xác nhận

Đã xác nhận (2026-11): điểm CNC2 mới teach là đúng; CNC5 đối diện CNC6, 1/3/5 cùng hàng và
quay mặt về 2/4/6; chuyển động cặp 3/4 và 5/6 làm giống cặp 1/2; điểm CNC3..6 và cửa
tạm lấy theo cặp 1/2. Còn chờ kiểm tra: mục 1, 2 dưới đây; mục 3 giữ nguyên hiện trạng.
Ghi chú mục "vị trí trục khi chạy P1/P5–P8": dự kiến robot về điểm trung gian/Home rồi trục mới
về vị trí cặp 1/2 — hiện code chưa thêm gì cho việc này (P2/P3/P4 thoát vẫn dừng ở cửa).


1. **Kẹp chuck CNC3..CNC6**: DO79/DI79 (lẻ) và DO78/DI78 (chẵn) có được PLC định tuyến
   theo AO2 (P3 → CNC3/CNC4, P4 → CNC5/CNC6) không? Nếu không, cần thêm tín hiệu mới trong map
   và sửa 2 chỗ có nhãn `[CNC36]`, mỗi P dùng chỉ số IO literal riêng.
2. **AI16** chứa **số CNC (1..6)** hay **số vị trí trục Axis1 (1 = CNC12, 2 = CNC34, 3 = CNC56)**?
   Code gốc và bản bổ sung đều giả định là số CNC 1..6. Nếu thực tế là vị trí trục 1..3 thì
   phần chọn cửa Home của code gốc **đã sai từ trước**, và phải đổi ngưỡng.
3. PLC chỉ được di chuyển trục Axis1 khi robot ở Home hoặc ở Door (sau DO17 / DO16), và
   phải bật DI20/DI21 **sau khi** trục đã dừng đúng vị trí.
4. Khí thổi DO74/DO75: PLC chọn van/thời gian theo AO2 + Case (đã có thanh ghi `TimeAirBlowCNC1..6`).

## 7. Quy trình chạy thử (đề xuất)

1. Đưa trục tới `Pos CNC34`. Teach cửa `p_door_c3`, `p_door_c4`. Dạy lại các điểm theo **đúng thứ tự** CNC3: `p_c3_air_v1`, `p_c3_air_switch_tool`,
   `p_c3_load_wait`, `p_c3_load`, `p_c3_load_end`, `p_c3_unload_wait`, `p_c3_unload`,
   `p_c3_unload_down`. Với CNC4: `p_c4_air_v1`, `p_c4_air`, `p_c4_load_wait`, `p_c4_load`,
   `p_c4_load_end`, `p_c4_unload_wait`, `p_c4_unload`. Dán giá trị joint vào file.
2. Đặt AI3 ≤ 20 (tốc độ thấp nhất). Chạy từng Case DI35 → DI36 → DI37 → DI38, tay đặt sẵn trên nút dừng.
   Kiểm tra log `ACTIVE POINT SET CNC3 CNC4`, kiểm tra không có `WARNING AI16`.
3. Thử Home DI90 khi robot dừng ở từng điểm của CNC3/CNC4 (LoadWait, Load, LoadEnd,
   UnloadWait, Unload, UnloadDown, AirC4). Log phải báo `HOME ACTUAL POSITION MATCH ...`
   và robot phải lùi đúng đường.
4. **Chạy lại toàn bộ test của CNC1/CNC2** (regression), vì phần Home đã đổi cách kiểm tra ±5°.
5. Lặp lại cho `Pos CNC56` (P4, DI40..43, `p_door_c5`, `p_door_c6`, `p_c5_*`, `p_c6_*`).
6. Lần nạp đầu: chạy DI90 Home một lần ở tốc độ thấp để xác nhận lệnh `door_c1_keep_j6_joint[i] = p_odd_door[i]` được bộ điều khiển chấp nhận.

## 8. Chạy thử trong Simulation khi không giả lập được IO

Thư mục `sim/` chứa 2 chương trình **chỉ dùng trong chế độ Simulation**, sinh tự động từ
`jamaguchi_cnc36.txt` bằng `sim/tao_sim.py` (khối chuyển động và khối Home được chép nguyên văn).
Mọi bước chờ tín hiệu PLC được thay bằng `sleep` + log `SIM SKIP WAIT DIxx`; mọi lệnh ghi DO/AO bị bỏ.

| File | Kiểm tra gì |
|---|---|
| `sim/sim_test1_motion.txt` | Cặp 1 → 2 → 3, mỗi cặp chạy Case 29 → 30 → 31 → 32: vào bằng cửa → chuyển động Case → ra bằng cửa. Quan sát robot ảo đi đúng đường, không báo lỗi tầm với / kine_inverse. Log phải có `ACTIVE POINT SET CNC1 CNC2`, `...CNC3 CNC4`, `...CNC5 CNC6`. |
| `sim/sim_test2_home.txt` | 18 phép thử Home: robot MoveJ thẳng tới 1 điểm dạy rồi chạy khối DI90 nguyên văn. So dòng `SIM TEST n EXPECT MATCH ...` với dòng `HOME ACTUAL POSITION MATCH ...` ngay sau nó, và robot phải lùi về Door rồi HomeLocation. |

Sau khi teach điểm CNC3..6 vào `jamaguchi_cnc36.txt`, sinh lại 2 file này
(`python tao_sim.py ../jamaguchi_cnc36.txt .`) rồi chạy lại để kiểm tra điểm mới trong Simulation trước khi lên máy thật.
