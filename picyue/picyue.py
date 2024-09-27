import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
from paddleocr import PaddleOCR
import cv2
import numpy as np

class OCRApp:
    def __init__(self, master):
        self.master = master
        self.master.title("PaddleOCR GUI")
        self.master.geometry("800x600")

        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')

        self.canvas = tk.Canvas(self.master, width=700, height=500)
        self.canvas.pack(pady=10)

        self.load_button = tk.Button(self.master, text="Load Image", command=self.load_image)
        self.load_button.pack(pady=10)

        self.image = None
        self.photo = None

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if file_path:
            self.image = Image.open(file_path)
            self.image.thumbnail((700, 500))
            self.photo = ImageTk.PhotoImage(self.image)
            self.canvas.config(width=self.image.width, height=self.image.height)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            self.process_image(file_path)

    def process_image(self, file_path):
        img = cv2.imread(file_path)
        result = self.ocr.ocr(img, cls=True)

        for line in result:
            points = line[0]
            text = line[1][0]
            confidence = line[1][1]

            # Convert points to canvas coordinates
            scaled_points = [
                (int(p[0] * self.image.width / img.shape[1]), 
                 int(p[1] * self.image.height / img.shape[0])) 
                for p in points
            ]

            # Draw bounding box
            self.canvas.create_polygon(scaled_points, outline='red', fill='')

            # Add text label
            x, y = scaled_points[0]
            self.canvas.create_text(x, y-10, text=f"{text} ({confidence:.2f})", fill='red', anchor=tk.SW)

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRApp(root)
    root.mainloop()