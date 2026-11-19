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
| 4 | Tín hiệu kẹp chuck: map chỉ có **DO79/DI79 = chuck CNC1**, **DO78/DI78 = chuck CNC2** | **Đã xác nhận:** tín hiệu dùng chung, PLC chọn máy kẹp theo Process đang chạy → robot không cần sửa |
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
8. **Chú thích tại DO79/DI79 và DO78/DI78**: tín hiệu kẹp chuck dùng chung cho P2/P3/P4, PLC chọn máy theo Process (đã xác nhận).

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
tạm lấy theo cặp 1/2. Tín hiệu kẹp chuck: dùng chung, PLC chọn máy theo Process (mục 1 đã xong). AI16 = số CNC 1..6 (mục 2 đã xong). mục 3 giữ nguyên hiện trạng.
Ghi chú mục "vị trí trục khi chạy P1/P5–P8": dự kiến robot về điểm trung gian/Home rồi trục mới
về vị trí cặp 1/2 — hiện code chưa thêm gì cho việc này (P2/P3/P4 thoát vẫn dừng ở cửa).


1. ~~Kẹp chuck CNC3..CNC6~~ — **đã xác nhận**: DO79/DI79 (lẻ), DO78/DI78 (chẵn) dùng chung; PLC chọn máy theo Process.
   (nội dung cũ) **Kẹp chuck CNC3..CNC6**: DO79/DI79 (lẻ) và DO78/DI78 (chẵn) có được PLC định tuyến
   theo AO2 (P3 → CNC3/CNC4, P4 → CNC5/CNC6) không? Nếu không, cần thêm tín hiệu mới trong map
   và sửa 2 chỗ có nhãn `[CNC36]`, mỗi P dùng chỉ số IO literal riêng.
2. ~~AI16~~ — **đã xác nhận với PLC: AI16 = số CNC 1..6**, đúng với giả định trong code.
   (nội dung cũ) **AI16** chứa **số CNC (1..6)** hay **số vị trí trục Axis1 (1 = CNC12, 2 = CNC34, 3 = CNC56)**?
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

## 9. Chu trình sản phẩm thực tế (đã xác nhận 2026-11)

* CNC1/3/5 = **công đoạn 1**, CNC2/4/6 = **công đoạn 2**. Cặp 3/4 và 5/6 chạy giống cặp 1/2; trục Axis1 đưa robot giữa các cặp.
* Chu trình hiện tại (thứ tự do PLC gọi):
  1. **P1** lấy phôi thô bằng Tool Load (DI28).
  2. **Unload CNC lẻ** bằng Tool Unload → **Load CNC lẻ** bằng Tool Load (P2/P3/P4 Case2 → Case1).
  3. **P8** đổi tool: chuyển sản phẩm từ Tool Unload sang Tool Load.
  4. **Unload CNC chẵn** → **Load CNC chẵn** (Case4 → Case3).
  5. **P7** đặt thành phẩm vào cụm kiểm tra.
* **P5 (xì khí) và P6 (Bavia) hiện đang bị bỏ qua** phía PLC (không bật DI22/DI23). Code robot giữ nguyên, không cần sửa.
* AI16 = số CNC 1..6 (đã xác nhận) – đúng với giả định trong code.

## 10. Kết quả chạy Simulation (2026-11-16, log xuất từ JAKA)

* **Test 1 (chuyển động)**: chạy trọn 4 lần liên tiếp (chế độ lặp đang bật), mỗi lần 332 dòng log,
  đủ 12 Case kết thúc đúng (`... END AT ...`), đủ `ACTIVE POINT SET CNC1 CNC2 / CNC3 CNC4 / CNC5 CNC6`. Không lỗi.
* **Test 2 (Home DI90)**: 18/18 phép thử nhận diện đúng điểm, đúng bộ điểm theo AI16, đúng cửa
  (CNC lẻ → DoorC1, CNC chẵn → DoorC2), cả 18 lần đều về HomeLocation và bật DO16. Không lỗi.
* 2 lỗi `Parsing failed` trong log (22:36:29 và 23:21:24) là lỗi của file test (gán `di64 = 1`,
  dấu ngoặc trong chuỗi log), đã sửa; chương trình chính không có 2 mẫu này.
* Rút ra: JAKA chỉ báo lỗi cú pháp khi **chạy tới dòng đó**, nên nạp được chưa chứng minh cả file đúng.

## 11. Thay đổi cụm đảo tool P8 (2026-11-17)

* Cập nhật 2 điểm vừa teach lại:
  `p_load_daotool_wait = [-5.321,90.910,100.547,165.270,-140.056,-48.007]` (TCP Z 355.4),
  `p_load_daotool = [-5.320,91.879,104.347,160.501,-140.055,-48.007]` (TCP Z 325.4) — chỉ khác 30 mm theo Z.
* Đoạn LOAD_DAOTOOL_WAIT → LOAD_DAOTOOL đổi từ `movj` sang **`movl`** (đi thẳng xuống):
  `p_load_daotool_pose = kine_forward(p_load_daotool)` rồi `movl(p_load_daotool_pose,0,speed_movel,200,0)`
  — cùng cấu trúc với P1 Pick (`movj` tới Wait có blend 10 → `movl` xuống điểm chính xác).
* Tính lại vùng nhận diện Home `p_load_daotool_segment_min/max` = hai điểm mới ±5°.
* Đoạn đi lên (LOAD_DAOTOOL → WAIT sau khi kẹp) **giữ nguyên `movj`** như cũ.
* Test Simulation mới: `sim/sim_test3_p8.txt`.
* **Test 3 (P8) trong Simulation 2026-11-16 23:53: đạt** — chạy tới `SIM P8 TEST END`, qua đoạn MoveL mới,
  kẹp/nhả tool, lùi về Wait và về HomeLocation, không lỗi.

## 12. Checklist log khi chạy thật chu trình máy 1 (P2: Unload CNC1 → Load CNC1)

Log lấy đúng thứ tự từ `jamaguchi_cnc36.txt`. Trong ngoặc là tín hiệu PLC phải gửi.

1. Khởi động: `FULL PROCESS START MODBUS HIGH` → `WAIT DI90 HOME OR DI18-DI27 PROCESS ON` → `STARTUP SCAN DI18-DI27`
2. Vào P2 (DI19): `DI19 ON ENTER P2 CNC1 CNC2` → `DO16 OFF ROBOT LEAVING HOME` → `CURRENT P2 AO2 2 DO19 ON` →
   **`ACTIVE POINT SET CNC1 CNC2`** (mới) → `WAIT DI83 DOORC1 OR DI84 DOORC2 ON` → (DI83) `DI83 ON ENTRY MOVEJ DOORC1` →
   `WAIT DI30 ON OR DI31 ON OR DI32 ON OR DI33 ON`
3. Unload CNC1 (DI31): `DI31 ON P2 CASE2 UNLOAD CNC1` → **`ACTIVE POINT SET CNC1 CNC2`** →
   `P2C2 ... AIRC1V1` → (DI74) → `P2C2 ... AIRSWITCHTOOL` → (DI75) → `P2C2 ... C1UNLOADWAIT` → `P2C2 ... C1UNLOAD` →
   (DI64) → `... C1UNLOADDOWN COMPLETE` → `P2C2 END AT C1UNLOADWAIT` → `P2 CASE2 DO31 ON HOLD UNTIL DI17 ON` →
   (DI17 lên rồi xuống) `DI17 ON RETURN TO PROCESS SCAN` → `WAIT DI17 OFF` → `CURRENT P2 WAIT DI30 ...`
4. Load CNC1 (DI30): `DI30 ON P2 CASE1 LOAD CNC1` → **`ACTIVE POINT SET CNC1 CNC2`** →
   `P2C1 ... AIRC1V1` → (DI74) → `P2C1 ... AIRSWITCHTOOL` → (DI75) → `P2C1 ... C1LOADWAIT` → `P2C1 ... C1LOAD` →
   (DI61) → `P2C1 ... C1LOADEND` → (DI79 kẹp chuck) → `... RETURN C1LOAD` → `... RETURN C1LOADWAIT` →
   `P2C1 END AT C1LOADWAIT` → `P2 CASE1 DO30 ON HOLD UNTIL DI17 ON` → (DI17) `DI17 ON RETURN TO PROCESS SCAN`
5. Thoát (DI16): `DI16 EXIT PROCESS BY SAFE REVERSE PATH` → `EXIT VIA SELECTED DOORC1` →
   `P2 P3 P4 EXIT COMPLETE AT SELECTED DOOR NO HOME MOVE` → `DI16 ON EXIT CURRENT PROCESS` → `AO2 0 NO ACTIVE PROCESS` →
   `DO17 ON WAIT DI16 OFF` → (DI16 xuống) `DI16 OFF DO17 OFF` → `WAIT DI90 HOME OR DI18-DI27 PROCESS ON`

Không được xuất hiện: `WARNING AI16 ...`, mọi dòng `... ABORTED ...`, `DI16 CASE NOT COMPLETE HOME MOVE SKIPPED`.
Khác code gốc: chỉ thêm các dòng `ACTIVE POINT SET CNC1 CNC2`.

## 13. Chạy thật trên máy (2026-11-17)

* **Chu trình CNC1/CNC2 (P2) với `jamaguchi_cnc36.txt`: chạy được, đúng quy trình** (người vận hành xác nhận).

## 14. Cập nhật 2026-11-17

* **Điểm teach lại**: `p_c1_load`, `p_c1_load_wait`, `p_c1_load_end` (CNC1) và `p_load_m2_wait`, `p_load_c2`,
  `p_end_load_m2v1` (CNC2). Điểm tạm CNC3/CNC5 chép theo CNC1 mới, CNC4/CNC6 chép theo CNC2 mới.
* **Home từ máy chẵn (2/4/6)**: khi robot dừng lưng chừng trong vùng trước chuck (không khớp điểm teach nào),
  trước đây MoveL thẳng ra DoorC2. Nay chọn theo J6:
  * J6 gần hướng Tool Load (≈ +44°) → MoveL về **LoadM2_Wait** → DoorC2 → Home
  * J6 gần hướng Tool Unload (≈ −135°) → MoveL về **UnloadM2_Wait** → DoorC2 → Home
  * J6 hướng thổi khí (≈ −47°) → giữ như cũ: MoveL thẳng ra DoorC2 (ngược đường vào AirC2v1)
  Ngưỡng là trung điểm giữa J6 các điểm đang dùng, tự theo điểm teach. Tốc độ lùi 30 mm/s.
  Khi dừng **đúng** điểm teach (LoadC2, EndLoad, UnloadM2...) vẫn lùi theo đường cũ (đã qua Wait).
  Máy lẻ (1/3/5) không đổi.
* Test 2 thêm phép thử 19, 20 (robot cao hơn LoadC2 / UnloadM2 40 mm).

## 15. Home từ vùng nguy hiểm: luôn MoveL về điểm Wait rồi mới ra cửa (cả máy lẻ và chẵn)

Áp dụng khi robot ở trong vùng nguy hiểm CNC lẻ (`home_c1_danger_side = 1`) hoặc CNC chẵn
(`home_c2_danger_side = 1`) và **không khớp điểm teach nào**. Chọn điểm Wait theo J6 (tool đang hướng vào chuck):

| J6 | Máy lẻ 1/3/5 | Máy chẵn 2/4/6 |
|---|---|---|
| Hướng Tool Load (≈ +44°) | MoveL → C1LoadWait → DoorC1 → Home | MoveL → LoadM2_Wait → DoorC2 → Home |
| Hướng Tool Unload (≈ −135°) | MoveL → C1UnloadWait → DoorC1 → Home | MoveL → UnloadM2_Wait → DoorC2 → Home |
| Hướng thổi khí (≈ −45°) | MoveL → AirC1v1 → DoorC1 → Home | MoveL → AirC2v1 → DoorC2 → Home |

* Ngưỡng = trung điểm J6 giữa các điểm đang dùng (tự theo điểm teach). MoveL lùi ở 30 mm/s.
* Khi khớp điểm AirC2 (đã có trong danh sách nhận diện): nay cũng lùi AirC2 → AirC2v1 → DoorC2.
* Test 2 thêm phép thử 21–24 (CNC1 load/unload nâng 40 mm, AirSwitchTool, AirC2v1).

## 16. Zone monitor (DO56/DO57/DO58) – `zone/zone_monitor.txt`

* Chạy dạng **Sub-thread** (khối Run Program → Sub-thread1) song song với chương trình chính, cập nhật cả khi robot đang chạy.
* DO56: X_user > 679.362 (qua DoorC1, phía máy lẻ). DO57: X_user < −365.358 (qua DoorC2, phía máy chẵn).
  DO58: Y_user > 1187.165 (= Y Pick 1237.165 − 50). Ghi DO khi đổi trạng thái, kèm log ON/OFF.
* Đã xác nhận: tọa độ màn hình teach là hệ user `usrfr_thanh`; robot chỉ ra Pick khi trục ở vị trí CNC1/2
  nên DO58 có nghĩa đúng.
* Còn chờ: cú pháp script của khối Run Program Sub-thread; PLC map DO56–DO58.
* Cách chạy đã chốt (2026-11-18): chương trình khung kéo thả `New Program` =
  **Run Program: Sub-thread1 → `check_workzone`** (Sub script `checkworkzone` = `zone_monitor.txt`),
  sau đó **Loop 1 → Sub script chính (`jamaguchi_cnc36.txt`)**. Không sửa code chính.
  Nếu cần `set_tool_id(1)` / `set_user_frame_id(7)`: đặt trong khung kéo thả trước khối Run Program.
* Test song song trong Simulation: Sub-thread1 = `zone/sim_zone_monitor.txt`, Sub chính = `sim/sim_test1_motion.txt`.
* Test song song trong Simulation 2026-11-18 09:00 (`sim_main_simple` + `sim_zone_monitor`): **luồng phụ chạy song song đúng**,
  bit đổi trong lúc robot đang di chuyển. Phát hiện: robot đứng ở Door đã bị tính là trong máy (ngưỡng = đúng X cửa),
  và Pick (X_user 683.8) vượt mặt phẳng DoorC1 nên DO56 bật ở Pick. Đã sửa: khoảng đệm `zone_door_margin = 20` mm
  sau mặt phẳng cửa. Theo yêu cầu: DO56 vẫn bật khi ở Pick (PLC tự xử lý), không loại trừ vùng Pick.

## 17. Kết quả máy thật 2026-11-18

* **Home từ vùng nguy hiểm → MoveL về Wait → cửa → Home: chạy đúng trên máy thật.** Giữ nguyên.
* **P8 đảo tool (điểm mới + MoveL xuống Load_daotool): chạy đúng.** Giữ nguyên (đoạn lên vẫn MoveJ, blend 10).
* Test song song 09:14 trong Simulation cho kết quả giống lần 09:00 (DO56 bật ở Pick và ở DoorC1) → nghi Sub-thread
  vẫn dùng bản chưa có `zone_door_margin`, hoặc Simulation dùng tool khác tool "thanh". Từ nay dòng khởi động in
  `ZONE MONITOR STARTED MARGIN 20 PICK Y 1187` để nhận biết phiên bản.

## 18. Chốt zone_monitor (2026-11-18)

* Dùng **`zone/zone_monitor.txt`** (so sánh X/Y bằng công thức đổi Base → usrfr_thanh), không dùng
  `set_user_frame_id` / `set_tool_id` (theo tài liệu JAKA, hai lệnh này đổi thiết lập chung của cả robot,
  sẽ ảnh hưởng chương trình chính). Bản userframe đã xóa.
* Test thực tế ngày 2026-11-19, checklist:
  1. Khung kéo thả: Run Program Sub-thread1 → `check_workzone` (dán `zone_monitor.txt`), rồi Sub chính `jamaguchi_cnc36`.
  2. Log khởi động phải có `ZONE MONITOR STARTED MARGIN 20 PICK Y 1187`.
  3. Ghi lại tool / user frame đang chọn khi chạy (ngưỡng đo với tool "thanh").
  4. Quan sát DO56/57/58 trên màn hình IO: đứng ở cửa → OFF; vào CNC lẻ → DO56 ON; CNC chẵn → DO57 ON; Pick → DO58 ON.
  5. Chỉnh `zone_door_margin` nếu bit bật quá sớm/muộn quanh cửa.

## 19. Chương trình riêng `drop/jamaguchi_cnc1_drop.txt` (2026-11-18)

Sinh từ `jamaguchi_cnc36.txt` bằng `drop/tao_drop.py`; chỉ đổi P7, mọi phần khác giữ nguyên.
* Chu trình: P2 Unload CNC1 (DI31) → DI17 → DI16 thoát (robot ở DoorC1) → PLC bật **P7 (DI24) → Case DI53**:
  MoveJ HomeLocation → MoveJ điểm trên cao (điểm thả + Z 100 mm) → MoveL xuống điểm thả →
  DO65/DI65 nhả Tool Unload → MoveL nhấc Z 100 mm → MoveJ HomeLocation → DO53 Case Comp.
* `p_drop` = [-9.049,127.295,101.570,128.230,-234.974,129.924] (teach 2026-11-18, usrfr_thanh + tool_thanh:
  X −112.925, Y 1317.358, Z 353.706). Y_user 1317 > 1187 nên **DO58 (vùng Pick) sẽ ON khi robot ở điểm thả**.
* `pose_add` (tài liệu JAKA 3.4.2.1): cộng XYZ trực tiếp, hướng R_res = R_pos2·R_pos1 → offset [0,0,100,0,0,0]
  = nhấc thẳng đứng, giữ hướng tool.
* Kiểm tra an toàn: nếu `pose_add` không cho ra đúng +100 mm theo Z (X/Y lệch > 5 mm), Case bị bỏ,
  log `P7C1 DROP SKIPPED LIFT OFFSET IS NOT STRAIGHT UP CHECK POSE_ADD`.
* Home DI90: thay vùng nhận diện P7 cũ bằng đoạn điểm thả ↔ điểm trên cao (±5°, tự tính từ điểm);
  đường lùi = MoveL thẳng lên điểm trên cao (30 mm/s) → Home.
* Test Simulation: `drop/sim_drop_test.txt`, `drop/sim_drop_home_test.txt`.

## 20. Cú pháp script đã kiểm chứng trên bộ điều khiển (Simulation, 2026-11-19)

| Cú pháp | Kết quả |
|---|---|
| `&&`, `\|\|`, `!=`, kết hợp có ngoặc | dùng được |
| `if / elif / else / end` | dùng được |
| Phép tính trong điều kiện `if(...)`, chỉ số mảng hằng `a[0]` | dùng được |
| Gán phần tử mảng từ phần tử mảng khác `b[0] = a[0]`, gán nguyên mảng `c = a` | dùng được |
| `!` (NOT) | **không dùng được** (Wrong data format), kể cả với biến số nguyên → dùng phép so sánh ngược |
| Phép tính khi gán **không bọc ngoặc** `z = x * 2.0 + y - 1.0`, `j = j + 1` | **không dùng được** |
| Phép tính khi gán **bọc cả biểu thức trong ngoặc** `j = (j + 1)`, `xu = (0.7057 * (t[0] - 345.833) + ...)`, `b[2] = (a[2] + 100.0)` | **dùng được** (test 3, P1–P9) |
| `while` với biến đếm, chỉ số mảng là biến `a[j]` (trong gán và trong `if`) | **dùng được** |
| Dấu ngoặc `( )` trong chuỗi log | **không dùng được** |
| Mảng viết trực tiếp làm tham số hàm `pose_add(p,[0,0,50,0,0,0])` | **không dùng được** → khai báo biến mảng trước |
| Hàm tự định nghĩa | không có trong bản phần mềm này |

## 21. Rút gọn bằng cú pháp đã kiểm chứng (2026-11-19)

* `zone/zone_monitor.txt`: 75 → 57 dòng (tính X/Y_user một lần vào biến, `&&` + `elif` cho ghi DO khi đổi trạng thái).
* Simulation 2026-11-19: `sim_drop_test` **đạt** (pose_add nhấc đúng 100 mm); `sim_drop_home_test` **đạt**
  (vòng `while` 6 khớp nhận diện đoạn điểm thả, MoveL thẳng lên rồi về Home).
* `drop/jamaguchi_cnc1_drop.txt`: P7 dùng `wait_input`, kiểm tra an toàn 1 dòng `||`;
  nhận diện đoạn điểm thả khi Home dùng vòng `while` 6 khớp (63 → 12 dòng).

## 22. Checklist chạy thật chương trình thả hàng `drop/jamaguchi_cnc1_drop.txt`

Chuẩn bị: giữ `jamaguchi_cnc36.txt` trên bộ điều khiển (tên khác) để đổi lại; AI3 ≤ 20; tool_thanh + usrfr_thanh.
1. **Kiểm tra điểm trước khi chạy chương trình**: Manual → Joint Move tới `p_drop`; xác nhận Tool Unload hướng xuống,
   đúng độ cao nhả hàng. Jog Z+ 100 mm (hệ usrfr_thanh) xem phía trên thoáng.
2. **Chu trình CNC1** (như cũ): DI19 → DI83 → DI31 Unload CNC1 → DO31 → DI17 → DI16 thoát (robot ở DoorC1).
3. **Thả hàng**: PLC bật DI24 (P7) → log `CURRENT P7 AO2 7 DO24 ON WAIT DI53 ON OR DI16 ON` → bật DI53.
   Log phải theo thứ tự: `CURRENT P7 CASE1 DROP OUTSIDE RUN` → `P7C1 HOMELOCATION COMPLETE` →
   `P7C1 DROP ABOVE COMPLETE` → `P7C1 DROP COMPLETE` → `P7C1 DO65 ON WAIT DI65 ON UNCLAMP TOOL UNLOAD`
   (PLC nhả Tool Unload, trả DI65) → `P7C1 LIFT Z 100 COMPLETE` → `P7C1 END AT HOMELOCATION` →
   `P7 CASE1 DO53 ON HOLD UNTIL DI17 ON` → DI17 → DI16 thoát P7 (robot ở Home, DO16 ON).
4. Không được thấy: `P7C1 DROP SKIPPED ...`, `P7C1 ABORTED ...`.
5. **Home DI90 quanh điểm thả**: cho robot dừng giữa đường xuống/lên (Pause/Stop), bật DI90 →
   `HOME ACTUAL POSITION IN DROP SEGMENT` → MoveL thẳng lên → Home.
6. Nếu chạy kèm `zone_monitor`: ở điểm thả DO58 ON (Y_user 1317 > 1187) – bình thường.

## 23. Kết quả tìm hiểu user frame (Simulation Zu5, tool 0, 2026-11-19)

* `get_atl_tcp_pose()` và `kine_forward()` **trả về theo user frame đang chọn** (đổi khi `set_user_frame_id`).
  → Comment cũ "returns Base" chỉ đúng khi chương trình chạy với user frame 0. Phần vùng nguy hiểm khi Home
  chạy đúng trên máy thật ⇒ nhiều khả năng lúc chạy chương trình user frame = 0 (cần xác nhận).
* `movl(...,1,...)` dịch theo trục của user frame đang chọn (hệ 0: trục base; hệ 7: chéo 45° = trục user). Đúng tài liệu.
* `movl(...,2,...)` dịch theo trục tool (tool 0 ở Home: trục Z nghiêng).
* Giá trị đọc ở hệ 7 chưa khớp công thức trong ±1,5 mm (góc xoay thì khớp) → đang đo mức lệch: `syntax/sim_userframe_learn2.txt`.

## 24. User frame khi chạy chương trình trên robot thật (2026-11-19)

* Màn hình Manual hiển thị usrfr_thanh / tool_thanh, nhưng `syntax/real_frame_probe.txt` chạy trên robot thật
  báo **`PROBE ACTIVE FRAME = BASE 0`**: lúc chạy chương trình, user frame = 0 (base).
* ⇒ `get_atl_tcp_pose()` / `kine_forward()` trả về tọa độ Base; **công thức Base→usrfr_thanh của code gốc là đúng**,
  vùng nguy hiểm khi Home **không lỗi**. (Nhận định "đổi hệ hai lần" trước đó là sai, đã hủy.)
* `zone_monitor` dùng lại công thức (tính 1 lần vào `zone_xu`/`zone_yu`). Sai số công thức so với hệ 7 < 2 mm (X, Y).
* Tool khi chạy chương trình: chưa xác nhận – `syntax/real_tool_probe.txt`.
