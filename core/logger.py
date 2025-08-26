import os
import logging
from datetime import datetime

def setup_logging():
    """
    애플리케이션의 파일 기반 로깅 시스템을 설정합니다.

    - 로그 레벨은 .env 파일의 LOG_LEVEL 값으로 설정 (기본값: INFO).
    - 'logs' 디렉터리에 실행 시점마다 고유한 타임스탬프를 가진 로그 파일을 생성합니다.
        - (예: logs/bot_2025-07-05_14-30-00.log)
    """
    # 1. .env 파일 또는 환경 변수에서 로그 레벨 가져오기
    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # 2. 로그 포맷터 생성
    # [시간] [레벨] [로거 이름] - [메시지]
    log_format = logging.Formatter(
        '%(asctime)s - %(levelname)-8s - %(name)-25s - %(message)s'
    )

    # 3. 루트 로거 설정
    # 애플리케이션의 모든 로거는 이 설정을 상속합니다.
    # 가장 낮은 레벨로 설정하여 모든 핸들러가 로그를 개별적으로 필터링하게 합니다.
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 기존에 연결된 핸들러가 있다면 모두 제거 (재호출 시 중복 방지)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 4. 파일 핸들러 설정 (실행 시마다 새 파일 생성)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(project_root, 'logs')
    
    os.makedirs(log_dir, exist_ok=True)
    log_filename = datetime.now().strftime("bot_%Y-%m-%d_%H-%M-%S.log")
    
    file_handler = logging.FileHandler(os.path.join(log_dir, log_filename), encoding='utf-8')
    file_handler.setLevel(log_level) # .env에서 설정한 레벨 이상만 파일에 기록
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    # 5. discord.py 라이브러리 로거 설정
    # discord.py의 로그도 파일에 함께 기록되도록 레벨을 설정합니다.
    # (DEBUG는 너무 상세하므로 INFO 레벨로 선택)
    logging.getLogger('discord').setLevel(logging.INFO)
    logging.getLogger('discord.http').setLevel(logging.WARNING) # API 요청 로그는 경고 이상만

    logging.info("Logging system has been initialized.")
    logging.debug(f"File log level set to: {log_level_str}")
    _cleanup_old_logs(log_dir)

def _cleanup_old_logs(log_dir: str, max_files: int = 10):
    """지정된 디렉터리에서 가장 오래된 로그 파일을 정리합니다."""
    logging.info("Checking for old log files...")
    try:
        files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".log")]
        files.sort(key=os.path.getctime)

        if len(files) > max_files:
            files_to_delete = files[:len(files) - max_files]
            for f in files_to_delete:
                os.remove(f)
                logging.info(f"Removed old log file: {f}")
    except OSError as e:
        logging.error(f"Error cleaning up old log files: {e}")