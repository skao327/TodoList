import tkinter as tk
from tkinter import simpledialog, messagebox, font

class TodoApp:
    def __init__(self, master, user_name="예빈"):
        self.master = master
        self.user_name = user_name
        master.title(f"{self.user_name}님의 할 일 목록")
        master.geometry("500x600") #창 크기

        self.tasks = [] #할 일 저장할 리스트 (딕셔너리 형태)

        self.title_label = tk.Label(master, text=f"{self.user_name}님의 할 일 목록", font=("Helvetica", 18, "bold"))
        self.title_label.pack(pady=10)

        self.entry_frame = tk.Frame(master) #할 일 입력 
        self.entry_frame.pack(pady=10, fill=tk.X, padx=20)

        self.task_entry = tk.Entry(self.entry_frame, width=40, font=("helvetica", 12))
        self.task_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.task_entry.bind("<Return>", self.add_task_event) #엔터키로 추가

        self.add_button = tk.Button(self.entry_frame, text="추가", command=self.add_task_ui, font=("Helvetica", 10, "bold"), bg="#4CAF50", fg="white")
        self.add_button.pack(side=tk.LEFT, padx=5)

        self.tasks_list_frame_container = tk.Frame(master)  #할 일 목록 표시(스크롤 되게) 
        self.tasks_list_frame_container.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.tasks_list_frame_container)
        self.scrollbar = tk.Scrollbar(self.tasks_list_frame_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)   #실제 할 일 들어가는 프레임 

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        #초기 할 일 렌더링?

        self.render_tasks()

    def add_task_event(self, event):    #엔터키 이벤트 홀더더
        self.add_task_ui()

    def add_task_ui(self):
        """UI를 통해 할 일을 추가하는 메소드"""
        task_text = self.task_entry.get().strip()
        if not task_text:
            messagebox.showwarning("입력 오류", "할 내용을 입력해주세요.")
            return
        
        completed_var = tk.BooleanVar(value=False)

        task_data = {
            "text": task_text,
            "completed_var": completed_var,
            "label_widget": None,
            "checkbox_widget": None
        }

        completed_var.trace_add("write", lambda *args, td=task_data: self.toggle_completion(td))

        self.task.append(task_data)
        self.task_entry.delete(0, tk.END)
        self.render_tasks()

    def toggle_completion(self, task_data):
        """체크박스 상태 변경 시 호출되어 할 일 완려 상태를 토글하고 UI 업데이트"""
        label_widget = task_data.get("label_wideget")
        if not label_widget:
            return
        
        current_font = font.Font(font=label_widget.cget("font"))
        is_completed = task_data["completed_var"].get()

        if is_completed:
            label_widget.config(font=(current_font.name, current_font.cget("size"), "overstrike"), fg="grey")
        else:
            label_widget.config(font=(current_font.name, current_font.cget("size"), "normal"), fg="black")

    def render_tasks(self):
        """할 일 목록을 UI에 표시하는 메소드. 기존 목록 지우고 새로 그림"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.tasks:
            no_tasks_label = tk.Label(self.scrollable_frame, text="등록된 할 일이 없습니다.", font=("Helvetica", 12), fg="grey")
            no_tasks_label.pack(pady=20)
            return
        
        for idx, task_data in enumerate(self.tasks):
            task_item_frame = tk.Frame(self.scrollable_frame, bd=1, relief=tk.SOLID, padx=5, pady=5)
            task_item_frame.pack(fill=tk.X, pady=3, padx=5)

            checkbox = tk.Checkbutton(
                task_item_frame,
                variable=task_data["completed_var"]
            )
            checkbox.pack(side=tk.LEFT)
            task_data["checkbox_widget"] = checkbox
            
            task_label = tk.Label(task_item_frame, text=task_data["text"], font=("Helvetica", 12), anchor="w", justify=tk.LEFT)
            task_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            task_data["label_widget"] = task_label

            self.toggle_completion(task_data)

        self.scrollable_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def main():
        root = tk.Tk()
        app = TodoApp(root, user_name="예빈")

        root.mainloop()

        if __name__ == "__main__":
            main()