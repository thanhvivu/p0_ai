# PROGRESS – JAKA cobot nạp phôi 6 máy CNC (cập nhật 2026-11-26)

Chi tiết kỹ thuật, kết quả test, checklist: `jaka_cnc/PHAN_TICH.md` (mục 1–24).
Branch: `claude/robot-cnc-code-analysis-ji9l5h`.

## Mục tiêu tổng thể
- Robot JAKA trên trục Axis1 phục vụ 6 CNC (2 hàng: lẻ 1/3/5 = công đoạn 1, chẵn 2/4/6 = công đoạn 2).
- Mở rộng chương trình script cũ (chạy CNC1/2) sang CNC3..6, giữ nguyên logic đã chạy ở nhà máy.
- Phụ: chương trình riêng "CNC1 + thả hàng ra ngoài"; bit cảnh báo vùng làm việc cho PLC; rút gọn code.

## File chính (`jaka_cnc/`)
- `jamaguchi_goc.txt`: code gốc. `jamaguchi_cnc36.txt`: bản đang chạy (CNC1..6, đánh dấu `[CNC36]`).
- `tools/build_cnc36.py`: dựng `cnc36` từ code gốc (`tr -d '\r' < jamaguchi_goc.txt > orig.txt; python build_cnc36.py orig.txt jamaguchi_cnc36.txt`). **Sửa cnc36 qua script này**, không sửa tay.
- `sim/tao_sim.py` → `sim_test1_motion` (Case CNC), `sim_test2_home` (24 phép thử DI90), `sim_test3_p8`.
- `drop/tao_drop.py` → `jamaguchi_cnc1_drop.txt` + `sim_drop_test`, `sim_drop_home_test`.
- `zone/tao_zone.py` → `zone_monitor.txt` (Sub-thread), `sim_zone_monitor`, `sim_zone_test`; `sim_main_simple.txt`.
- `syntax/`: các test cú pháp, `real_frame_probe.txt`, `real_tool_probe.txt` (chạy được trên máy thật).

## Đã hoàn thành
- cnc36: bộ điểm active `p_odd_*`/`p_even_*` theo `cnc_pair` (P2→1, P3→2, P4→3; Home theo AI16); cửa theo cặp;
  Home ±5° tính từ điểm; vùng nguy hiểm → MoveL về Load/Unload/Air Wait → cửa (cả lẻ & chẵn).
- Máy thật OK: chu trình CNC1/2; Home qua Wait; P8 đảo tool (điểm mới + MoveL xuống Load_daotool).
- Điểm CNC1/CNC2 Load cập nhật lần teach 2026-11-17 (lần 2). CNC3..6 + cửa = PLACEHOLDER (chép CNC1/CNC2).
- Simulation đạt: Test 1, Test 2 (18/18 cũ), Test 3, sim_drop_test, sim_drop_home_test, test song song zone.
- Drop program: P7 Case DI53 = Home → trên cao (+100 Z) → MoveL xuống → DO65/DI65 → nhấc → Home; Home nhận
  diện đoạn điểm thả bằng vòng `while` 6 khớp. Điểm thả teach: `[-9.049,127.295,101.570,128.230,-234.974,129.924]`.
- zone_monitor (DO56 lẻ, DO57 chẵn, DO58 Pick), đã rút gọn (57 dòng), chạy dạng Sub-thread1 trong khung kéo thả.

- 2026-11-26: bộ điểm mới + Tool Load tròn/vuông (PHAN_TICH mục 25) đã đưa vào cnc36 qua `tools/build_cnc36.py`;
  P8 3 đoạn thẳng → MoveL; sinh lại sim/drop/zone. **Chưa test** (Simulation + máy thật).

## Đang làm dở
- **Ưu tiên 1: chạy thật chương trình thả hàng** theo checklist `PHAN_TICH.md` mục 22 (chưa có kết quả).
- zone_monitor: ngưỡng đang đo bằng tool_thanh nhưng chương trình chạy với tool khác (xem dưới) → chờ số đo lại.
- Test 2 bản 24 phép thử (19–24: vùng nguy hiểm qua Wait) chưa chạy lại trong Simulation (máy thật đã OK).

## Quyết định đã chốt (lý do)
- Teach điểm bằng góc khớp; MoveL luôn qua cặp `kine_forward` + `movl` (đúng với mọi tool/user frame).
- Thả hàng = file riêng, P7 làm trigger (không đụng bản cnc36 đang chạy).
- Chưa rút gọn `jamaguchi_cnc36.txt` (đang chạy ổn; ưu tiên drop test). Ước giảm được ~400–500 dòng.
- zone_monitor chạy Sub-thread (khung kéo thả: Run Program Sub-thread1 → check_workzone, rồi Sub chính),
  không đặt `set_user_frame_id`/`set_tool_id` (thiết lập chung toàn robot).
- DO56 vẫn bật ở Pick nếu X vượt ngưỡng (PLC tự xử lý); đệm cửa `zone_door_margin = 20` mm.
- Tín hiệu kẹp chuck DO79/DI79 (lẻ), DO78/DI78 (chẵn) dùng chung; PLC chọn máy theo Process. AI16 = số CNC 1..6.
- P5 (xì khí), P6 (Bavia) đang bỏ qua phía PLC; code giữ nguyên.

## Cú pháp JAKA đã kiểm chứng (bộ điều khiển này)
- Dùng được: `&&`, `||`, `!=`, `if/elif/else/end`, `while`, chỉ số mảng là biến, gán `b[i] = a[i]`,
  **phép tính khi gán phải bọc ngoặc**: `j = (j + 1)`, `xu = (0.7057 * (t[0] - 345.833) + ...)`.
- Không dùng được: `!`; phép tính khi gán không bọc ngoặc; dấu `( )` trong chuỗi log; mảng viết trực tiếp
  làm tham số hàm `pose_add(p,[0,0,50,0,0,0])`; gán `di64 = 1` cho biến đã dùng với `get_digital_input`;
  hàm tự định nghĩa (bản phần mềm không có).
- JAKA chỉ báo lỗi cú pháp khi **chạy tới dòng đó** → phải chạy thật qua từng nhánh (dùng file sim).
- `pose_add`: cộng XYZ trực tiếp, giữ hướng. `movl` rel_flag 0/1 (user frame)/2 (tool).

## Vấn đề còn tồn tại / đã thử không được
- **Lúc chạy chương trình: user frame = 0 (base)** (probe máy thật), dù màn hình Manual hiện usrfr_thanh →
  công thức Base→usrfr_thanh của code gốc là ĐÚNG. (Từng kết luận sai "đổi hệ hai lần" – đã hủy.)
- **Tool lúc chạy ≠ tool_thanh** (probe: Pick lệch X > 100 mm, Y < 5 mm; có thể là tool 0). Ảnh hưởng
  ngưỡng zone_monitor và vùng nguy hiểm Home; KHÔNG ảnh hưởng chuyển động hay drop program.
- Simulation model Zu5 khác robot thật (A5 – A510003020) → không dùng mô phỏng để kiểm ngưỡng tọa độ.
- Home chưa nhận diện P1 Pick/PickWait (DI90 ở Pick → MoveJ sang cửa CNC qua nhánh AI16).
- Không đọc được www.jaka.com từ môi trường cloud → tài liệu lệnh do người dùng chụp gửi.

## Bước tiếp theo
1. Test bản 2026-11-26: Simulation Test 1/2/3 → máy thật P1, P2 (CNC1 tròn, CNC2 vuông), P8 ở tốc độ thấp.
1b. Chạy thật drop program (`PHAN_TICH.md` mục 22), gửi log.
2. Đo với tool 0 + usrfr_thanh: X DoorC1, X DoorC2, Y Pick → cập nhật ngưỡng `zone/tao_zone.py`
   (hoặc chọn đặt `set_tool_id(1)` đầu chương trình – phải test lại toàn chu trình).
3. PLC map DO56–DO58; chạy zone_monitor thật.
4. Teach CNC3..6 (máy lẻ 9 điểm, chẵn 7 điểm + cửa) → sửa `tools/build_cnc36.py` → sinh lại sim → test → P3/P4 thật.
5. (Khi được đồng ý) rút gọn cnc36 bằng cú pháp đã kiểm chứng; thêm nhận diện Pick cho Home.
