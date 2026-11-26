# PROGRESS – JAKA cobot nạp phôi 6 máy CNC (cập nhật 2026-11-26)

Chi tiết kỹ thuật, kết quả test, checklist: `jaka_cnc/PHAN_TICH.md` (mục 1–25).
Branch: `claude/robot-cnc-code-analysis-ji9l5h`.

## Mục tiêu
- Robot JAKA (A5, A510003020) trên trục Axis1 phục vụ 6 CNC: lẻ 1/3/5 = công đoạn 1, chẵn 2/4/6 = công đoạn 2.
- Mở rộng script cũ (CNC1/2) sang CNC3..6, giữ logic đã chạy ở nhà máy. Phụ: chương trình "CNC1 + thả hàng",
  bit vùng làm việc cho PLC, rút gọn code.

## Kiến trúc
**Chương trình chính `jaka_cnc/jamaguchi_cnc36.txt`** (một script, không có hàm; `while(1)` quét 0,1 s):
- Header: khai báo điểm (góc khớp), cờ, reset DO. Vòng quét: AI3 → tốc độ; DI16 thoát Process; DI90 Home;
  chọn Process DI18..27 (P1..P10); trong Process: DI17 trả Case, chọn Case, thực thi Case, DO Case Comp.
- CNC: P2/P3/P4 dùng chung 4 Case (29 Load lẻ, 30 Unload lẻ, 31 Load chẵn, 32 Unload chẵn) với bộ điểm active
  `p_odd_*`/`p_even_*` chọn theo `cnc_pair` (P2→1, P3→2, P4→3; DI90 theo AI16 = số CNC 1..6).
- Home DI90: nhận diện điểm (TCP ±20 mm + khớp ±5° tính từ điểm), đoạn P7/P8 (mảng min/max), vùng nguy hiểm
  (công thức Base→usrfr_thanh) → MoveL về Load/Unload/Air Wait → cửa; dự phòng AI16 → hướng gần nhất → MoveJ Home.
  `home_route_door_done` = đã tới điểm an toàn (không phải đã ở Home); bước cuối luôn MoveJ `p_home_location`.
- Chuyển động: MoveL = `kine_forward(joint)` + `movl` (về đúng góc khớp với mọi tool/user frame);
  MoveJ tới điểm có offset = `kine_forward` + `pose_add` + `kine_inverse(ref, pose)` + `movj`.
**Công cụ sinh file (sửa ở đây, không sửa tay):**
- `tools/build_cnc36.py` (code gốc `jamaguchi_goc.txt` → cnc36): `tr -d '\r' < jamaguchi_goc.txt > orig.txt;
  python build_cnc36.py orig.txt jamaguchi_cnc36.txt`. Mọi điểm mới thêm vào đây (dict theo số dòng code gốc).
- `drop/tao_drop.py` → `jamaguchi_cnc1_drop.txt` (+ sim). `zone/tao_zone.py` → `zone_monitor.txt` (+ sim).
- `sim/tao_sim.py` → test Simulation 1/2/3. `syntax/`: test cú pháp, `real_frame_probe`, `real_tool_probe` (máy thật).
**Chạy song song:** khung kéo thả `New Program` = Run Program Sub-thread1 → `check_workzone` (zone_monitor), rồi Sub chính.

## Trạng thái điểm (2026-11-26)
- Tool Load có 2 đầu: **tròn** (Load_Tron) cho Pick + CNC1/3/5; **vuông** (Load_vuong) cho CNC2/4/6 sau P8 đảo tool.
  Chung xi lanh DO60/DO61. TCP chỉ khác 6 mm theo Z tool → không dùng `set_tool_id` trong code.
- Đã cập nhật: pick/pickwait, C1Unload/Wait (**Down = Unload**), c1load/wait/end (tròn), CNC2 Load = bộ vuông,
  c2_unload/wait, unload_daotool, load_daotool/wait (vuông), **Home mới** [-45,56.711,106.885,194.140,-264.961,-45]
  (cả `p_process6_safe`). Giữ: Door, Air C1/C2, TG. Dự phòng: `p_c2_tron_load_*` (CNC2 đầu tròn, chọn model sau).
- P8: unload_daotool xuống/lên và load_daotool xuống/lên đều MoveL.
- CNC3..6 + cửa = PLACEHOLDER (chép CNC1 tròn / CNC2 vuông). Điểm thả (drop) `[-9.049,127.295,101.570,128.230,-234.974,129.924]`.

## Đang làm dở
- **Test máy thật bản 2026-11-26** (AI3 ≤ 20): P1 Pick (đầu tròn), Unload/Load CNC1, P8 (3 đoạn MoveL mới),
  Load CNC2 đầu vuông, Unload CNC2, DI90 giữa đoạn P8 và tại C1Unload, các MoveJ với Home mới (J6 xoay 93,7°).
- Chạy thật drop program (`PHAN_TICH.md` mục 22).
- zone_monitor: ngưỡng đo bằng tool_thanh nhưng chương trình chạy tool khác → chờ đo lại với tool 0.

## Quyết định đã chốt (lý do)
- **Chỉ tạo file test Simulation khi người dùng yêu cầu**; hiện test trực tiếp robot thật.
- Hỏi người dùng tài liệu khi chưa chắc cú pháp/lệnh (không đoán); www.jaka.com không truy cập được từ cloud.
- Teach bằng góc khớp; không đổi tool/user frame trong code (thiết lập chung toàn robot, ảnh hưởng zone_monitor).
- Thả hàng = file riêng, P7 (DI24/DI53) làm trigger; Home+100 Z bằng `pose_add`, có kiểm tra 99–101 mm.
- Chưa rút gọn cnc36 (đang chạy ổn); ước giảm ~400–500 dòng khi được đồng ý.
- zone_monitor: DO56 X_user > 679.362+20, DO57 X_user < −365.358−20, DO58 Y_user > 1187.165; đổi trạng thái mới ghi DO + log.
- Kẹp chuck DO79/DI79 (lẻ), DO78/DI78 (chẵn) dùng chung, PLC chọn máy theo Process. P5/P6 đang bỏ qua (PLC).

## Cú pháp JAKA đã kiểm chứng
- Được: `&&`, `||`, `!=`, `if/elif/else/end`, `while`, chỉ số mảng là biến, `b[i] = a[i]`, gán nguyên mảng,
  **phép tính khi gán phải bọc ngoặc** `j = (j + 1)`. Không được: `!`, tính toán khi gán không ngoặc,
  `( )` trong chuỗi log, mảng viết trực tiếp làm tham số hàm, `di64 = 1` cho biến đọc DI, hàm tự định nghĩa.
- Lỗi cú pháp chỉ báo khi chạy tới dòng đó. `pose_add`: cộng XYZ, giữ hướng. `movl` rel_flag 0 / 1 user / 2 tool.

## Bug / rủi ro đã biết
- Lúc chạy chương trình user frame = 0 (probe) → công thức Base→usrfr_thanh đúng (kết luận "đổi hệ hai lần" đã hủy).
- **Tool lúc chạy ≠ tool_thanh** (probe: Pick lệch X > 100 mm) → ngưỡng zone_monitor và vùng nguy hiểm Home
  lệch khoảng chiều dài tool theo X. Không ảnh hưởng chuyển động/drop.
- **MoveL 0 mm** (C1Unload → C1UnloadDown) chưa chạy lần nào: nếu báo lỗi → bỏ lệnh đó trong Case 30.
- Home chưa nhận diện P1 Pick/PickWait (DI90 ở Pick → MoveJ sang cửa CNC qua nhánh AI16).
- Mảng `*_min/*_max` cũ (CNC1/2, cửa) còn khai báo nhưng không dùng; chỉ `p_load/unload_daotool_segment_*`,
  `p_process7_unload_segment_*` còn dùng (phải tính lại khi teach lại các điểm đó).
- Simulation (Zu5) khác robot thật → không dùng để kiểm ngưỡng tọa độ.

## Bước tiếp theo
1. Test máy thật bản 2026-11-26 (mục "Đang làm dở"), gửi log nếu lỗi.
2. Chạy thật drop program.
3. Đo X DoorC1, X DoorC2, Y Pick với tool 0 + usrfr_thanh → cập nhật `zone/tao_zone.py`; PLC map DO56–58.
4. Teach CNC3..6 (lẻ 9 điểm + cửa, chẵn 7 điểm + cửa) → `tools/build_cnc36.py` → test P3/P4.
5. Khi được đồng ý: rút gọn cnc36; thêm nhận diện Pick cho Home.
