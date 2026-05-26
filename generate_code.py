#!/usr/bin/env python3
"""
万米霖-授权码生成器（管理员使用）

tkinter GUI 版本。输入设备ID，生成激活码。
"""

import tkinter as tk
from tkinter import messagebox

from app.activation import generate_activation_code


class AuthCodeApp:
    """授权码生成器 GUI"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("万米霖-授权码生成器")
        self.root.geometry("480x380")
        self.root.resizable(False, False)

        # 背景色
        self.root.configure(bg="#f5f5f7")

        self._build_ui()

    def _build_ui(self):
        bg = "#f5f5f7"

        # 标题
        title_label = tk.Label(
            self.root,
            text="万米霖-授权码生成器",
            font=("Microsoft YaHei", 18, "bold"),
            bg=bg,
            fg="#1d1d1f",
        )
        title_label.pack(pady=(30, 5))

        subtitle_label = tk.Label(
            self.root,
            text="输入用户的设备ID, 生成对应的激活码",
            font=("Microsoft YaHei", 10),
            bg=bg,
            fg="#86868b",
        )
        subtitle_label.pack(pady=(0, 20))

        # 输入区域
        input_frame = tk.Frame(self.root, bg=bg)
        input_frame.pack(padx=40, fill="x")

        input_label = tk.Label(
            input_frame,
            text="设备ID:",
            font=("Microsoft YaHei", 11),
            bg=bg,
            fg="#1d1d1f",
            anchor="w",
        )
        input_label.pack(fill="x")

        self.device_id_var = tk.StringVar()
        self.device_id_entry = tk.Entry(
            input_frame,
            textvariable=self.device_id_var,
            font=("Consolas", 13),
            relief="solid",
            bd=1,
        )
        self.device_id_entry.pack(fill="x", pady=(5, 0), ipady=6)
        self.device_id_entry.bind("<Return>", lambda e: self._generate())

        # 生成按钮
        self.generate_btn = tk.Button(
            self.root,
            text="生成激活码",
            font=("Microsoft YaHei", 12, "bold"),
            bg="#0071e3",
            fg="white",
            activebackground="#0060c0",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self._generate,
        )
        self.generate_btn.pack(pady=20, ipadx=30, ipady=6)

        # 结果区域
        self.result_frame = tk.Frame(self.root, bg="#e8e8ed", relief="solid", bd=1)

        result_title = tk.Label(
            self.result_frame,
            text="生成结果",
            font=("Microsoft YaHei", 10, "bold"),
            bg="#e8e8ed",
            fg="#1d1d1f",
            anchor="w",
        )
        result_title.pack(fill="x", padx=12, pady=(10, 4))

        self.result_text = tk.Text(
            self.result_frame,
            font=("Consolas", 12),
            bg="#e8e8ed",
            fg="#1d1d1f",
            relief="flat",
            height=3,
            wrap="word",
            state="disabled",
            cursor="arrow",
        )
        self.result_text.pack(fill="x", padx=12, pady=(0, 4))

        # 复制按钮
        self.copy_btn = tk.Button(
            self.result_frame,
            text="复制激活码",
            font=("Microsoft YaHei", 10),
            bg="#34c759",
            fg="white",
            activebackground="#2da44e",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self._copy_code,
        )
        self.copy_btn.pack(pady=(0, 10), ipadx=16, ipady=3)

        # 初始隐藏结果区域
        self._current_code = ""

    def _generate(self):
        device_id = self.device_id_var.get().strip()
        if not device_id:
            messagebox.showwarning("提示", "请输入设备ID")
            self.device_id_entry.focus_set()
            return

        device_id = device_id.upper()
        code = generate_activation_code(device_id)
        self._current_code = code

        # 显示结果
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", f"设备ID:  {device_id}\n激活码:  {code}")
        self.result_text.configure(state="disabled")

        # 展示结果区域
        self.result_frame.pack(padx=40, fill="x", pady=(0, 20))

    def _copy_code(self):
        if not self._current_code:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self._current_code)
        self.copy_btn.configure(text="已复制!")
        self.root.after(1500, lambda: self.copy_btn.configure(text="复制激活码"))


def main():
    root = tk.Tk()
    AuthCodeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
