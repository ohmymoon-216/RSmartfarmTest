import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import paho.mqtt.client as mqtt
import json
import math
import time
from datetime import datetime
import threading


class RobotSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("로봇 위치 시뮬레이터")
        self.root.geometry("800x700")

        # MQTT 클라이언트 설정
        self.mqtt_client = None
        self.is_running = False
        self.simulation_thread = None

        # 상태 정보 발송 관련
        self.status_running = False
        self.status_thread = None

        # 사용 가능한 로봇 목록
        self.robot_ids = ['ROBOT-001', 'ROBOT-002', 'ROBOT-003']

        # 각 로봇별 위치 정보 저장 (robot_id: {'x': float, 'y': float})
        self.robot_positions = {
            'ROBOT-001': {'x': 0.0, 'y': 0.0},
            'ROBOT-002': {'x': 0.0, 'y': 0.0},
            'ROBOT-003': {'x': 0.0, 'y': 0.0}
        }

        # 각 로봇별 상태 정보 저장
        self.robot_states = {
            'ROBOT-001': {'battery': 80, 'role': 'EMPTY', 'operational_status': 'IDLE'},
            'ROBOT-002': {'battery': 80, 'role': 'EMPTY', 'operational_status': 'IDLE'},
            'ROBOT-003': {'battery': 80, 'role': 'EMPTY', 'operational_status': 'IDLE'}
        }

        # 현재 위치 추적
        self.current_x = 0
        self.current_y = 0

        self.setup_ui()

    def setup_ui(self):
        # 탭 컨트롤 생성
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # 탭 1: 위치 시뮬레이션
        position_tab = ttk.Frame(notebook)
        notebook.add(position_tab, text="위치 시뮬레이션")

        # 탭 2: 상태 정보
        status_tab = ttk.Frame(notebook)
        notebook.add(status_tab, text="상태 정보")

        # 위치 시뮬레이션 탭 UI 설정
        self.setup_position_tab(position_tab)

        # 상태 정보 탭 UI 설정
        self.setup_status_tab(status_tab)

    def setup_position_tab(self, parent):
        # 메인 프레임
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # MQTT 브로커 설정
        mqtt_frame = ttk.LabelFrame(main_frame, text="MQTT 브로커 설정", padding="10")
        mqtt_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(mqtt_frame, text="브로커 주소:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.broker_entry = ttk.Entry(mqtt_frame, width=30)
        self.broker_entry.insert(0, "localhost")
        self.broker_entry.grid(row=0, column=1, padx=5)

        ttk.Label(mqtt_frame, text="포트:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.port_entry = ttk.Entry(mqtt_frame, width=10)
        self.port_entry.insert(0, "1883")
        self.port_entry.grid(row=0, column=3, padx=5)

        self.connect_btn = ttk.Button(mqtt_frame, text="브로커 연결", command=self.connect_mqtt)
        self.connect_btn.grid(row=0, column=4, padx=5)

        self.connection_status = ttk.Label(mqtt_frame, text="● 연결 안됨", foreground="red")
        self.connection_status.grid(row=0, column=5, padx=5)

        # 로봇 설정 프레임
        robot_frame = ttk.LabelFrame(main_frame, text="로봇 설정", padding="10")
        robot_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # 로봇 ID
        ttk.Label(robot_frame, text="로봇 ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.robot_id_combobox = ttk.Combobox(robot_frame, width=18, values=self.robot_ids, state='readonly')
        self.robot_id_combobox.set("ROBOT-001")
        self.robot_id_combobox.grid(row=0, column=1, padx=5, pady=5)
        self.robot_id_combobox.bind('<<ComboboxSelected>>', self.on_robot_id_changed)

        # 시작점
        ttk.Label(robot_frame, text="시작점 X:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.start_x_entry = ttk.Entry(robot_frame, width=20)
        self.start_x_entry.insert(0, "0")
        self.start_x_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(robot_frame, text="시작점 Y:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.start_y_entry = ttk.Entry(robot_frame, width=20)
        self.start_y_entry.insert(0, "0")
        self.start_y_entry.grid(row=2, column=1, padx=5, pady=5)

        # 도착점
        ttk.Label(robot_frame, text="도착점 X:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.end_x_entry = ttk.Entry(robot_frame, width=20)
        self.end_x_entry.insert(0, "100")
        self.end_x_entry.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(robot_frame, text="도착점 Y:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.end_y_entry = ttk.Entry(robot_frame, width=20)
        self.end_y_entry.insert(0, "50")
        self.end_y_entry.grid(row=4, column=1, padx=5, pady=5)

        # 속도
        ttk.Label(robot_frame, text="속도 (m/s):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.speed_entry = ttk.Entry(robot_frame, width=20)
        self.speed_entry.insert(0, "1.0")
        self.speed_entry.grid(row=5, column=1, padx=5, pady=5)

        # 업데이트 주기
        ttk.Label(robot_frame, text="업데이트 주기 (초):").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        self.update_interval_entry = ttk.Entry(robot_frame, width=20)
        self.update_interval_entry.insert(0, "0.5")
        self.update_interval_entry.grid(row=6, column=1, padx=5, pady=5)

        # 제어 버튼
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=10)

        self.start_btn = ttk.Button(control_frame, text="시뮬레이션 시작", command=self.start_simulation, state=tk.DISABLED)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.stop_btn = ttk.Button(control_frame, text="시뮬레이션 정지", command=self.stop_simulation, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5)

        # 현재 상태
        status_frame = ttk.LabelFrame(main_frame, text="현재 상태", padding="10")
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(status_frame, text="현재 위치:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.current_position_label = ttk.Label(status_frame, text="X: 0.0, Y: 0.0")
        self.current_position_label.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(status_frame, text="진행률:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.progress_label = ttk.Label(status_frame, text="0%")
        self.progress_label.grid(row=1, column=1, sticky=tk.W, padx=5)

        self.progress_bar = ttk.Progressbar(status_frame, length=400, mode='determinate')
        self.progress_bar.grid(row=2, column=0, columnspan=2, pady=5)

        # 로그 영역
        log_frame = ttk.LabelFrame(main_frame, text="메시지 로그", padding="10")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=90, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 로그 클리어 버튼
        ttk.Button(log_frame, text="로그 지우기", command=self.clear_log).grid(row=1, column=0, pady=5)

        # Grid 가중치 설정
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    def setup_status_tab(self, parent):
        # 메인 프레임
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # MQTT 연결 상태 표시
        status_info_frame = ttk.LabelFrame(main_frame, text="MQTT 연결 상태", padding="10")
        status_info_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(status_info_frame, text="상태 정보를 전송하려면 먼저 '위치 시뮬레이션' 탭에서 MQTT 브로커에 연결하세요.").grid(row=0, column=0, padx=5, pady=5)

        # 로봇 상태 설정 프레임
        robot_status_frame = ttk.LabelFrame(main_frame, text="로봇 상태 설정", padding="10")
        robot_status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        # 로봇 ID
        ttk.Label(robot_status_frame, text="로봇 ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.status_robot_id_combobox = ttk.Combobox(robot_status_frame, width=27, values=self.robot_ids, state='readonly')
        self.status_robot_id_combobox.set("ROBOT-001")
        self.status_robot_id_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.status_robot_id_combobox.bind('<<ComboboxSelected>>', self.on_status_robot_id_changed)

        # 배터리 레벨
        ttk.Label(robot_status_frame, text="배터리 레벨 (%):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        battery_frame = ttk.Frame(robot_status_frame)
        battery_frame.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

        self.battery_scale = ttk.Scale(battery_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=200)
        self.battery_scale.set(80)
        self.battery_scale.grid(row=0, column=0, padx=(0, 10))

        self.battery_value_label = ttk.Label(battery_frame, text="80%")
        self.battery_value_label.grid(row=0, column=1)

        self.battery_scale.config(command=self.on_battery_changed)

        # Role
        ttk.Label(robot_status_frame, text="역할 (Role):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.role_combobox = ttk.Combobox(robot_status_frame, width=27, values=["EMPTY", "CLEANING", "WATERING", "MONITORING", "FERTILIZING", "TRANSPLANTING", "HARVESTING"])
        self.role_combobox.set("EMPTY")
        self.role_combobox.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        self.role_combobox.bind('<<ComboboxSelected>>', self.on_role_changed)

        # Operational Status
        ttk.Label(robot_status_frame, text="작동 상태:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.operational_status_combobox = ttk.Combobox(robot_status_frame, width=27, values=["IDLE", "PREPARE", "MOVING", "WORKING", "CHARGING", "PAUSE", "STOP", "ERROR"])
        self.operational_status_combobox.set("IDLE")
        self.operational_status_combobox.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
        self.operational_status_combobox.bind('<<ComboboxSelected>>', self.on_operational_status_changed)

        # 전송 주기
        ttk.Label(robot_status_frame, text="전송 주기 (초):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.status_interval_entry = ttk.Entry(robot_status_frame, width=30)
        self.status_interval_entry.insert(0, "2.0")
        self.status_interval_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)

        # 제어 버튼
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=10)

        self.status_start_btn = ttk.Button(control_frame, text="상태 전송 시작", command=self.start_status_publishing, state=tk.DISABLED)
        self.status_start_btn.grid(row=0, column=0, padx=5)

        self.status_stop_btn = ttk.Button(control_frame, text="상태 전송 정지", command=self.stop_status_publishing, state=tk.DISABLED)
        self.status_stop_btn.grid(row=0, column=1, padx=5)

        # 현재 상태 표시
        current_status_frame = ttk.LabelFrame(main_frame, text="현재 전송 상태", padding="10")
        current_status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(current_status_frame, text="전송 상태:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.status_sending_label = ttk.Label(current_status_frame, text="정지", foreground="red")
        self.status_sending_label.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(current_status_frame, text="전송 횟수:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.status_count_label = ttk.Label(current_status_frame, text="0")
        self.status_count_label.grid(row=1, column=1, sticky=tk.W, padx=5)

        # 로그 영역
        log_frame = ttk.LabelFrame(main_frame, text="메시지 로그", padding="10")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        self.status_log_text = scrolledtext.ScrolledText(log_frame, height=15, width=90, wrap=tk.WORD)
        self.status_log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 로그 클리어 버튼
        ttk.Button(log_frame, text="로그 지우기", command=self.clear_status_log).grid(row=1, column=0, pady=5)

        # Grid 가중치 설정
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    def connect_mqtt(self):
        try:
            broker = self.broker_entry.get()
            port = int(self.port_entry.get())

            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self.on_mqtt_connect
            self.mqtt_client.on_disconnect = self.on_mqtt_disconnect

            self.log_message(f"MQTT 브로커에 연결 중... ({broker}:{port})")
            self.mqtt_client.connect(broker, port, 60)
            self.mqtt_client.loop_start()

        except Exception as e:
            messagebox.showerror("연결 오류", f"MQTT 브로커 연결 실패:\n{str(e)}")
            self.log_message(f"연결 오류: {str(e)}")

    def on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connection_status.config(text="● 연결됨", foreground="green")
            self.start_btn.config(state=tk.NORMAL)
            self.status_start_btn.config(state=tk.NORMAL)
            self.connect_btn.config(state=tk.DISABLED)
            self.log_message("MQTT 브로커에 연결되었습니다.")
            self.status_log_message("MQTT 브로커에 연결되었습니다.")
        else:
            self.connection_status.config(text="● 연결 실패", foreground="red")
            self.log_message(f"MQTT 연결 실패 (코드: {rc})")
            self.status_log_message(f"MQTT 연결 실패 (코드: {rc})")

    def on_mqtt_disconnect(self, client, userdata, rc):
        self.connection_status.config(text="● 연결 안됨", foreground="red")
        self.start_btn.config(state=tk.DISABLED)
        self.status_start_btn.config(state=tk.DISABLED)
        self.connect_btn.config(state=tk.NORMAL)
        self.log_message("MQTT 브로커와 연결이 끊어졌습니다.")
        self.status_log_message("MQTT 브로커와 연결이 끊어졌습니다.")

    def on_robot_id_changed(self, event):
        """위치 시뮬레이션 탭에서 로봇 ID 변경 시 호출"""
        # 선택된 로봇의 저장된 위치 값으로 UI 업데이트
        robot_id = self.robot_id_combobox.get()
        position = self.robot_positions[robot_id]

        # 시작점 업데이트
        self.start_x_entry.delete(0, tk.END)
        self.start_x_entry.insert(0, f"{position['x']:.2f}")
        self.start_y_entry.delete(0, tk.END)
        self.start_y_entry.insert(0, f"{position['y']:.2f}")

        # 현재 위치도 업데이트
        self.current_x = position['x']
        self.current_y = position['y']

        self.log_message(f"로봇 {robot_id} 선택됨 - 저장된 위치: X={position['x']:.2f}, Y={position['y']:.2f}")

    def on_status_robot_id_changed(self, event):
        """상태 정보 탭에서 로봇 ID 변경 시 호출"""
        # 선택된 로봇의 저장된 상태 값으로 UI 업데이트
        robot_id = self.status_robot_id_combobox.get()
        state = self.robot_states[robot_id]

        # 배터리, role, operational_status 업데이트
        self.battery_scale.set(state['battery'])
        self.battery_value_label.config(text=f"{state['battery']}%")
        self.role_combobox.set(state['role'])
        self.operational_status_combobox.set(state['operational_status'])

        self.status_log_message(f"로봇 {robot_id} 선택됨 - 배터리: {state['battery']}%, 역할: {state['role']}, 상태: {state['operational_status']}")

    def on_battery_changed(self, value):
        """배터리 레벨 변경 시 호출"""
        battery_level = int(float(value))
        self.battery_value_label.config(text=f"{battery_level}%")

        # 현재 로봇의 배터리 상태 저장
        robot_id = self.status_robot_id_combobox.get()
        self.robot_states[robot_id]['battery'] = battery_level

    def on_role_changed(self, event):
        """역할 변경 시 호출"""
        robot_id = self.status_robot_id_combobox.get()
        self.robot_states[robot_id]['role'] = self.role_combobox.get()

    def on_operational_status_changed(self, event):
        """작동 상태 변경 시 호출"""
        robot_id = self.status_robot_id_combobox.get()
        self.robot_states[robot_id]['operational_status'] = self.operational_status_combobox.get()

    def calculate_heading(self, dx, dy):
        """두 점 사이의 방향각 계산 (도 단위)"""
        angle = math.degrees(math.atan2(dy, dx))
        # 0-360도로 정규화
        if angle < 0:
            angle += 360
        return round(angle, 2)

    def start_simulation(self):
        try:
            robot_id = self.robot_id_combobox.get()
            start_x = float(self.start_x_entry.get())
            start_y = float(self.start_y_entry.get())
            end_x = float(self.end_x_entry.get())
            end_y = float(self.end_y_entry.get())
            speed = float(self.speed_entry.get())
            update_interval = float(self.update_interval_entry.get())

            if not robot_id:
                messagebox.showwarning("입력 오류", "로봇 ID를 입력해주세요.")
                return

            # 현재 위치를 시작점으로 초기화
            self.current_x = start_x
            self.current_y = start_y

            self.is_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)

            # 시뮬레이션 스레드 시작
            self.simulation_thread = threading.Thread(
                target=self.run_simulation,
                args=(robot_id, start_x, start_y, end_x, end_y, speed, update_interval)
            )
            self.simulation_thread.daemon = True
            self.simulation_thread.start()

            self.log_message(f"시뮬레이션 시작: {robot_id}")

        except ValueError as e:
            messagebox.showerror("입력 오류", "숫자 값을 올바르게 입력해주세요.")

    def run_simulation(self, robot_id, start_x, start_y, end_x, end_y, speed, update_interval):
        # 총 거리 계산
        dx = end_x - start_x
        dy = end_y - start_y
        total_distance = math.sqrt(dx ** 2 + dy ** 2)

        # 방향 계산
        heading = self.calculate_heading(dx, dy)

        # 정규화된 방향 벡터
        if total_distance > 0:
            dir_x = dx / total_distance
            dir_y = dy / total_distance
        else:
            self.log_message("시작점과 도착점이 동일합니다.")
            self.stop_simulation()
            return

        # 현재 위치
        current_x = start_x
        current_y = start_y
        traveled_distance = 0

        topic = f"robot/{robot_id}/position"

        while self.is_running and traveled_distance < total_distance:
            # 메시지 생성
            message = {
                "robot_id": robot_id,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "position": {
                    "x": round(current_x, 2),
                    "y": round(current_y, 2),
                    "z": 0
                },
                "heading": heading
            }

            # MQTT 메시지 발송
            if self.mqtt_client:
                self.mqtt_client.publish(topic, json.dumps(message))
                self.log_message(f"발송: {json.dumps(message, ensure_ascii=False)}")

            # UI 업데이트
            progress = (traveled_distance / total_distance) * 100
            self.root.after(0, self.update_ui, current_x, current_y, progress)

            # 다음 위치 계산
            time.sleep(update_interval)
            distance_step = speed * update_interval

            if traveled_distance + distance_step >= total_distance:
                # 마지막 위치로 이동
                current_x = end_x
                current_y = end_y
                traveled_distance = total_distance
            else:
                current_x += dir_x * distance_step
                current_y += dir_y * distance_step
                traveled_distance += distance_step

        # 최종 위치 메시지 발송
        if self.is_running:
            final_message = {
                "robot_id": robot_id,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "position": {
                    "x": round(end_x, 2),
                    "y": round(end_y, 2),
                    "z": 0
                },
                "heading": heading
            }

            if self.mqtt_client:
                self.mqtt_client.publish(topic, json.dumps(final_message))
                self.log_message(f"발송: {json.dumps(final_message, ensure_ascii=False)}")

            self.root.after(0, self.update_ui, end_x, end_y, 100)
            self.log_message(f"시뮬레이션 완료: 도착점 도달")

        self.root.after(0, self.stop_simulation)

    def update_ui(self, x, y, progress):
        self.current_x = x
        self.current_y = y
        self.current_position_label.config(text=f"X: {x:.2f}, Y: {y:.2f}")
        self.progress_bar['value'] = progress
        self.progress_label.config(text=f"{progress:.1f}%")

    def stop_simulation(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        if not self.is_running:
            # 현재 로봇의 위치를 딕셔너리에 저장
            robot_id = self.robot_id_combobox.get()
            self.robot_positions[robot_id]['x'] = self.current_x
            self.robot_positions[robot_id]['y'] = self.current_y

            # 현재 위치를 시작점으로 업데이트
            self.start_x_entry.delete(0, tk.END)
            self.start_x_entry.insert(0, f"{self.current_x:.2f}")
            self.start_y_entry.delete(0, tk.END)
            self.start_y_entry.insert(0, f"{self.current_y:.2f}")
            self.log_message(f"시뮬레이션 정지 - {robot_id} 위치 저장됨: X={self.current_x:.2f}, Y={self.current_y:.2f}")

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def start_status_publishing(self):
        try:
            robot_id = self.status_robot_id_combobox.get()
            interval = float(self.status_interval_entry.get())

            if not robot_id:
                messagebox.showwarning("입력 오류", "로봇 ID를 입력해주세요.")
                return

            if not self.mqtt_client:
                messagebox.showwarning("연결 오류", "먼저 MQTT 브로커에 연결해주세요.")
                return

            self.status_running = True
            self.status_start_btn.config(state=tk.DISABLED)
            self.status_stop_btn.config(state=tk.NORMAL)
            self.status_sending_label.config(text="전송 중", foreground="green")

            # 상태 전송 스레드 시작
            self.status_thread = threading.Thread(
                target=self.run_status_publishing,
                args=(robot_id, interval)
            )
            self.status_thread.daemon = True
            self.status_thread.start()

            self.status_log_message(f"상태 전송 시작: {robot_id}")

        except ValueError:
            messagebox.showerror("입력 오류", "전송 주기는 숫자로 입력해주세요.")

    def run_status_publishing(self, robot_id, interval):
        topic = f"robot/{robot_id}/status"
        count = 0

        while self.status_running:
            # 현재 UI 값 읽기
            battery_level = int(self.battery_scale.get())
            role = self.role_combobox.get()
            operational_status = self.operational_status_combobox.get()

            # 메시지 생성
            message = {
                "robot_id": robot_id,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "battery_level": battery_level,
                "role": role,
                "operational_status": operational_status
            }

            # MQTT 메시지 발송
            if self.mqtt_client and self.status_running:
                self.mqtt_client.publish(topic, json.dumps(message))
                count += 1
                self.root.after(0, self.update_status_count, count)
                self.status_log_message(f"발송: {json.dumps(message, ensure_ascii=False)}")

            # 다음 전송까지 대기
            time.sleep(interval)

    def update_status_count(self, count):
        self.status_count_label.config(text=str(count))

    def stop_status_publishing(self):
        self.status_running = False
        self.status_start_btn.config(state=tk.NORMAL)
        self.status_stop_btn.config(state=tk.DISABLED)
        self.status_sending_label.config(text="정지", foreground="red")

        # 현재 로봇의 상태를 딕셔너리에 저장
        robot_id = self.status_robot_id_combobox.get()
        self.robot_states[robot_id]['battery'] = int(self.battery_scale.get())
        self.robot_states[robot_id]['role'] = self.role_combobox.get()
        self.robot_states[robot_id]['operational_status'] = self.operational_status_combobox.get()

        self.status_log_message(f"상태 전송 정지 - {robot_id} 상태 저장됨")

    def status_log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_log_text.see(tk.END)

    def clear_status_log(self):
        self.status_log_text.delete(1.0, tk.END)


def main():
    root = tk.Tk()
    app = RobotSimulator(root)
    root.mainloop()


if __name__ == "__main__":
    main()