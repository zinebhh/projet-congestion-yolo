
import cv2

class VideoCamera:
    def __init__(self):
        # RTSP de la caméra de surveillance
        self.video = cv2.VideoCapture("rtsp://admin:admin123@192.168.1.10:554/stream1")

    def __del__(self):
        self.video.release()

    def get_frame(self):
        success, image = self.video.read()
        if not success:
            return None
        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()

