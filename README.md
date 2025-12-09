# 로봇 위치 시뮬레이터

tkinter와 MQTT를 사용한 로봇 위치 시뮬레이션 GUI 프로그램입니다.

## 기능

- 로봇 ID, 시작점, 도착점, 속도를 입력받아 로봇의 이동을 시뮬레이션
- 시작점부터 도착점까지 이동하면서 실시간으로 MQTT 메시지 발송
- JSON 형식의 위치 정보 (robot_id, timestamp, position, heading) 전송
- 진행 상황 시각화 및 메시지 로그 표시

## 설치 방법

```bash
pip install -r requirements.txt
```

또는 직접 설치:

```bash
pip install paho-mqtt
```

## 사용 방법

1. 프로그램 실행:
```bash
python robot_simulator.py
```

2. MQTT 브로커 설정:
   - 브로커 주소와 포트를 입력 (기본값: localhost:1883)
   - "브로커 연결" 버튼 클릭

3. 로봇 설정:
   - 로봇 ID 입력 (예: ROBOT-001)
   - 시작점 X, Y 좌표 입력
   - 도착점 X, Y 좌표 입력
   - 속도 입력 (m/s 단위)
   - 업데이트 주기 입력 (초 단위)

4. 시뮬레이션 실행:
   - "시뮬레이션 시작" 버튼 클릭
   - 로봇이 시작점에서 도착점까지 이동하며 MQTT 메시지 발송
   - 진행 상황을 진행률 바와 로그에서 확인
   - "시뮬레이션 정지" 버튼으로 중간에 중단 가능

## MQTT 메시지 형식

```json
{
  "robot_id": "ROBOT-001",
  "timestamp": "2025-11-09T10:00:00Z",
  "position": {
    "x": 10.5,
    "y": 5.25,
    "z": 0
  },
  "heading": 90.0
}
```

- **robot_id**: 로봇 고유 식별자
- **timestamp**: ISO 8601 형식의 UTC 시간
- **position**: 로봇의 현재 위치 (x, y, z 좌표)
- **heading**: 이동 방향 (0-360도)

## MQTT Topic 형식

```
robot/{robot_id}/position
```

예시: `robot/ROBOT-001/position`

## 테스트용 MQTT 브로커

로컬에서 테스트하려면 Mosquitto 브로커를 설치하세요:

### Windows
```bash
# Chocolatey 사용
choco install mosquitto

# 서비스 시작
net start mosquitto
```

### Linux
```bash
sudo apt-get install mosquitto mosquitto-clients
sudo systemctl start mosquitto
```

### Docker
```bash
docker run -it -p 1883:1883 eclipse-mosquitto
```

## MQTT 메시지 구독 (테스트)

다른 터미널에서 메시지를 확인하려면:

```bash
mosquitto_sub -h localhost -t "robot/#" -v
```

## 주요 파라미터

- **속도 (m/s)**: 로봇의 이동 속도
- **업데이트 주기 (초)**: MQTT 메시지 발송 간격
- **heading**: 시작점에서 도착점으로의 방향각 (0도=동쪽, 90도=북쪽, 180도=서쪽, 270도=남쪽)

## 주의사항

- MQTT 브로커가 실행 중이어야 합니다
- 네트워크 연결을 확인하세요
- 방화벽에서 MQTT 포트(기본 1883)가 열려있어야 합니다
