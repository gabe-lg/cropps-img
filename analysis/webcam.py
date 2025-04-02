import cv2
import threading


class Webcam:
    """ A thread that displays a live webcam feed """

    def __init__(self, src=0):
        self.stream = cv2.VideoCapture(src)  # Open webcam (0 = default webcam)
        self.ret, self.frame = self.stream.read()
        self.stopped = False

    def start(self):
        threading.Thread(target=self.update,
                         daemon=True).start()  # Start thread
        return self

    def update(self):
        while not self.stopped:
            self.ret, self.frame = self.stream.read()

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.stream.release()

    def main_thread(self, _):
        # Start the webcam video stream in a separate thread
        video_stream = self.start()

        # Display the video feed
        while True:
            frame = video_stream.read()
            if frame is None:
                continue

            cv2.imshow("Live Webcam", frame)

            # Press 'q' to exit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Stop the webcam and close windows
        video_stream.stop()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    webcam = threading.Thread(target=Webcam().main_thread, args=(1,))
    webcam.start()
