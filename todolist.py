import tkinter as tk
import mysql.connector
from tkinter import messagebox


class Todo:

    UNCHECKED = "☐ "
    CHECKED = "☑ "
    
    def __init__(self, root):
        self.root = root
        root.title("To-do List") #맨 위에 제목("To-do List")
        root.geometry("400x500") #사이즈

        #db세팅
        self.conn = mysql.connector.connect(
            host="127.0.0.1",
            user="todo_user",
            password="mypass123",
            database="todo_db"
)

        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT DATABASE();")
        print(self.cursor.fetchone())

        self.listbox_task_ids = []

        self.setup_gui()
        self.display_tasks()
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        self.task_entry=tk.Entry(self.root, width=30) #텍스트 입력창 
        self.task_entry.pack(pady=10)
        self.task_entry.bind("<Return>", self.add_task)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        self.add_button=tk.Button(button_frame, text="추가", width=10, command=self.add_task)
        self.add_button.pack(side=tk.LEFT, padx=5)

        list_frame = tk.Frame(self.root)
        list_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        self.task_listbox=tk.Listbox(self.root, width=40, height=15, selectmode=tk.SINGLE)
        self.task_listbox.bind('<<ListboxSelect>>', self.toggle_complete)

        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.task_listbox.yview)
        self.task_listbox.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.task_listbox.pack(side=tk.LEFT, fill="both", expand=True)


    def display_tasks(self): #할 일 불러오기(리스트박스를 초기화한 후 db에서 할 일 목록을 가져와 리스트박스에 표시(완료 항목엔 [완료]를 붙임))
        self.task_listbox.delete(0, tk.END)
        self.listbox_task_ids.clear()
        listbox_idx = 0
        try:
            self.cursor.execute("SELECT id, task, completed FROM todolists ORDER BY completed ASC, id ASC")
            for row in self.cursor.fetchall():
                task_id, task_text, completed_status = row
                prefix = self.CHECKED if completed_status else self.UNCHECKED
                display_text = prefix + task_text
                self.task_listbox.insert(tk.END, display_text)
                self.listbox_task_ids.append(task_id)

                if completed_status:
                    self.task_listbox.itemconfig(tk.END, {'fg': 'gray'})
                else:
                    self.task_listbox.itemconfig(tk.END, {'fg': 'black'})
        except mysql.connector.Error as e:
            messagebox.showerror("DB 오류", f"할 일 목록을 불러오는 중 오류 발생: {e}")

    def add_task(self, event=None):  #할 일 추가(텍스트 입력창에서 할 일을 가져와 db에 추가, 추가 후 입력창 비우고 목록을 새로고침)
        task = self.task_entry.get()
        if task:
            try:
                self.cursor.execute("INSERT INTO todolists (task) VALUES (%s)", (task,))
                self.conn.commit()
                print(f"할 일 추가: {task}")
                self.task_entry.delete(0, tk.END)
                self.display_tasks()
            except mysql.connector.Error as e:
                messagebox.showerror("DB 오류", f"할 일 추가 중 오류 발생: {e}")
        else:
            messagebox.showwarning("경고", "할 일을 입력해주세요.")

    def delete_task(self): #할 일 삭제(선택된 리스트 항목의 텍스트를 가져와 db에서 삭제, [완료]는 저장된 값이 아니므로 제거 후 비교, 삭제 후 새로고침)
        selected = self.task_listbox.curselection()
        if selected:
            index = selected[0]
            task_text = self.task_listbox.get(index).replace(" [완료]", "")
            self.cursor.execute("DELETE FROM todos WHERE task=%s", (task_text,))
            self.conn.commit()
            self.load_tasks()

    def toggle_complete(self, event=None): #완료 처리 토글(리스트박스에서 선택한 항목의 완료 여부를 반전시킴, 완료료된 상태면 미완료로, 미완료 상태면 완료로 바꿈, 업테이트 후 새로고침/)
        selected = self.task_listbox.curselection()
        if not selected:
            return
        
        selected_listbox_index = selected[0]

        taskID_toTOGGLE = self.listbox_task_ids[selected_listbox_index]

        try:
            self.cursor.execute("SELECT id, completed FROM todolists WHERE id=%s", (taskID_toTOGGLE,))
            result = self.cursor.fetchone()
            if result:
                current_status = result[1]
                new_status = 0 if current_status else 1
                self.cursor.execute("UPDATE todolists SET completed=%s WHERE id=%s", (new_status, taskID_toTOGGLE))
                self.conn.commit()
                self.display_tasks()
            else:
                messagebox.showinfo("오류", "완료 처리할 항목을 선택해주세요.")
        except mysql.connector.Error as e:
            messagebox.showerror("DB 오류", f"완료 상태 변경 중 오류 발생:{e}")

    def on_closing(self):
        if self.conn:
            self.conn.close()
            print("DB 연결이 종료되었습니다.")
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = Todo(root)
    root.mainloop()

#gui 구성
"""
delete_button=tk.Button(root,text="삭제",width=10)
delete_button.pack(pady=5)

complete_button=tk.Button(root,text="완료",width=10, command=toggle_complete)
complete_button.pack(pady=5)

load_tasks()

root.mainloop()

conn.close()
"""
