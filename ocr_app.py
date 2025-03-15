import os
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
import requests
import base64
from PIL import Image, ImageTk
import threading
import json
import io
import time
import configparser

class OCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OCR Image Processing App")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        self.folder_path = tk.StringVar()
        self.api_key = tk.StringVar()
        self.api_url = tk.StringVar()
        self.api_model = tk.StringVar()
        self.output_file = tk.StringVar()
        self.max_retries = tk.IntVar(value=3)  # 添加重试次数配置
        self.is_processing = False
        self.total_images = 0
        self.current_image = 0
        
        # 配置文件路径
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ocr_config.ini')
        
        # Default values
        self.api_url.set("https://api.openai.com/v1/chat/completions")
        self.api_model.set("gpt-4-vision-preview")
        self.output_file.set("ocr_results.txt")
        
        # 加载已保存的配置
        self.load_config()
        
        self.create_widgets()
        
        # 程序关闭时保存配置
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_widgets(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Settings frame
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="设置")
        
        # Results frame
        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text="结果")
        
        # === Settings frame content ===
        settings_frame.columnconfigure(1, weight=1)
        
        # Folder selection
        ttk.Label(settings_frame, text="图片文件夹:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.folder_path).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(settings_frame, text="浏览", command=self.browse_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # API Configuration
        ttk.Label(settings_frame, text="API 密钥:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.api_key, show="*").grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="API URL:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.api_url).grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="模型:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.api_model).grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="输出文件:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.output_file).grid(row=4, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # 添加重试次数配置
        ttk.Label(settings_frame, text="最大重试次数:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Spinbox(settings_frame, from_=1, to=10, textvariable=self.max_retries, width=5).grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Process button
        self.process_button = ttk.Button(settings_frame, text="开始处理", command=self.start_processing)
        self.process_button.grid(row=6, column=0, columnspan=3, pady=20)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(settings_frame, text="处理进度")
        progress_frame.grid(row=7, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=tk.EW, padx=5, pady=5)
        
        # Progress label
        self.progress_label = ttk.Label(progress_frame, text="就绪")
        self.progress_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        # Current image preview
        self.preview_label = ttk.Label(progress_frame, text="未选择图片")
        self.preview_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        # === Results frame content ===
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Results text area
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD)
        self.results_text.grid(row=0, column=0, sticky=tk.NSEW, padx=5, pady=5)
    
    def save_config(self):
        """保存当前配置到配置文件"""
        config = configparser.ConfigParser()
        config['API'] = {
            'api_key': self.api_key.get(),
            'api_url': self.api_url.get(),
            'api_model': self.api_model.get(),
            'max_retries': str(self.max_retries.get())
        }
        config['Settings'] = {
            'output_file': self.output_file.get(),
            'last_folder': self.folder_path.get()
        }
        
        try:
            with open(self.config_file, 'w') as f:
                config.write(f)
        except Exception as e:
            print(f"保存配置时出错: {str(e)}")
    
    def load_config(self):
        """从配置文件加载配置"""
        if not os.path.exists(self.config_file):
            return
        
        config = configparser.ConfigParser()
        try:
            config.read(self.config_file)
            
            if 'API' in config:
                if 'api_key' in config['API']:
                    self.api_key.set(config['API']['api_key'])
                if 'api_url' in config['API']:
                    self.api_url.set(config['API']['api_url'])
                if 'api_model' in config['API']:
                    self.api_model.set(config['API']['api_model'])
                if 'max_retries' in config['API']:
                    self.max_retries.set(int(config['API']['max_retries']))
            
            if 'Settings' in config:
                if 'output_file' in config['Settings']:
                    self.output_file.set(config['Settings']['output_file'])
                if 'last_folder' in config['Settings'] and os.path.exists(config['Settings']['last_folder']):
                    self.folder_path.set(config['Settings']['last_folder'])
                    self.count_images()
        except Exception as e:
            print(f"加载配置时出错: {str(e)}")
    
    def on_closing(self):
        """程序关闭时调用，保存配置"""
        self.save_config()
        self.root.destroy()
        
    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)
            self.count_images()
    
    def count_images(self):
        folder = self.folder_path.get()
        if not os.path.isdir(folder):
            return
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']
        image_files = [f for f in os.listdir(folder) if os.path.splitext(f.lower())[1] in image_extensions]
        self.total_images = len(image_files)
        self.progress_label.config(text=f"找到 {self.total_images} 张图片")
    
    def start_processing(self):
        if self.is_processing:
            messagebox.showinfo("处理中", "已经在处理图片了。")
            return
        
        # Validate inputs
        if not self.folder_path.get() or not os.path.isdir(self.folder_path.get()):
            messagebox.showerror("错误", "请选择有效的图片文件夹。")
            return
        
        if not self.api_key.get():
            messagebox.showerror("错误", "请输入您的API密钥。")
            return
        
        # Start processing in a separate thread
        self.is_processing = True
        self.process_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        
        # 保存当前配置
        self.save_config()
        
        # Clear results
        with open(self.output_file.get(), 'w', encoding='utf-8') as f:
            f.write("OCR 识别结果\n\n")
        
        self.results_text.delete(1.0, tk.END)
        
        # Start processing thread
        thread = threading.Thread(target=self.process_images)
        thread.daemon = True
        thread.start()
    
    def process_images(self):
        folder = self.folder_path.get()
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']
        image_files = [f for f in os.listdir(folder) if os.path.splitext(f.lower())[1] in image_extensions]
        
        self.total_images = len(image_files)
        self.current_image = 0
        
        for image_file in image_files:
            if not self.is_processing:
                break
            
            self.current_image += 1
            progress = (self.current_image / self.total_images) * 100
            
            # Update UI from main thread
            self.root.after(0, lambda p=progress, img=image_file: self.update_progress(p, img))
            
            # Process the image
            image_path = os.path.join(folder, image_file)
            result = self.perform_ocr(image_path)
            
            # Save result
            with open(self.output_file.get(), 'a', encoding='utf-8') as f:
                f.write(f"=== 图片: {image_file} ===\n")
                f.write(result)
                f.write("\n\n")
            
            # Update results in UI
            self.root.after(0, lambda txt=f"=== 图片: {image_file} ===\n{result}\n\n": self.update_results(txt))
        
        # Finish processing
        self.root.after(0, self.finish_processing)
    
    def update_progress(self, progress, image_name):
        self.progress_var.set(progress)
        self.progress_label.config(text=f"正在处理 {self.current_image} / {self.total_images}: {image_name}")
        
        # Display image preview
        try:
            image_path = os.path.join(self.folder_path.get(), image_name)
            img = Image.open(image_path)
            img.thumbnail((200, 200))
            photo = ImageTk.PhotoImage(img)
            
            # Need to keep a reference to prevent garbage collection
            self.current_photo = photo
            
            self.preview_label.config(image=photo, text="")
        except Exception as e:
            self.preview_label.config(image=None, text=f"无法预览: {str(e)}")
    
    def update_results(self, text):
        self.results_text.insert(tk.END, text)
        self.results_text.see(tk.END)
    
    def finish_processing(self):
        self.is_processing = False
        self.process_button.config(state=tk.NORMAL)
        self.progress_label.config(text=f"已完成处理 {self.total_images} 张图片")
        messagebox.showinfo("处理完成", f"已处理 {self.total_images} 张图片。结果保存到 {self.output_file.get()}")
    
    def perform_ocr(self, image_path):
        max_retries = self.max_retries.get()
        retry_count = 0
        retry_delay = 2  # 初始重试延迟（秒）
        
        while retry_count <= max_retries:
            try:
                # 更新界面显示当前重试状态
                if retry_count > 0:
                    self.root.after(0, lambda img=os.path.basename(image_path), rc=retry_count: 
                                  self.progress_label.config(text=f"正在处理 {self.current_image} / {self.total_images}: {img} (第 {rc} 次重试)"))
                
                # Encode image to base64
                with open(image_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                
                # Prepare API request
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key.get()}"
                }
                
                # Construct the message with the image
                payload = {
                    "model": self.api_model.get(),
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "请仔细分析这张图片中的所有文字内容，并提取出所有可见的文字。需要注意以下几点：\n\n1. 请保持文字的原始格式和段落结构\n2. 如果有表格，请尽量保持表格的结构\n3. 请按照阅读顺序从左到右、从上到下提取文字\n4. 如果有标题、小标题等，请保持其层次结构\n5. 如果文字清晰可见但因为角度、光线等原因难以识别，请尽量猜测并在旁边标注[不确定]\n6. 如果图片中有多种语言，请保持原有语言不要翻译\n7. 请忽略图片中的水印或背景噪音文字\n\n请只返回提取的文字内容，不需要其他解释或描述。"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{encoded_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 2000
                }
                
                # Send the request
                response = requests.post(
                    self.api_url.get(),
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                # Parse the result
                response_data = response.json()
                
                if 'error' in response_data:
                    if retry_count < max_retries:
                        retry_count += 1
                        time.sleep(retry_delay)
                        retry_delay *= 1.5  # 增加重试延迟时间
                        continue
                    return f"错误: {response_data['error']['message']} (已重试 {retry_count} 次)"
                
                # Extract text from the response
                result = response_data['choices'][0]['message']['content']
                return result
                
            except Exception as e:
                if retry_count < max_retries:
                    retry_count += 1
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # 增加重试延迟时间
                    continue
                return f"处理图片时出错: {str(e)} (已重试 {retry_count} 次)"
        
        return f"达到最大重试次数 ({max_retries})，无法处理图片"

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRApp(root)
    root.mainloop() 