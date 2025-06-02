import tkinter as tk
import mysql.connector
from tkinter import messagebox, simpledialog
from datetime import datetime, date, timedelta
import threading
import time
import traceback
import sys
class LoginWindow:
    def __init__(self, master, dbinfo):
        self.master = master
        self.dbinfo = dbinfo
        self.user_id = None

        master.title("로그인")
        tk.Label(master, text="아이디:").grid(row=0, column=0)
        tk.Label(master, text="비밀번호:").grid(row=1, column=0)
        self.entry_username = tk.Entry(master)
        self.entry_password = tk.Entry(master, show="*")
        self.entry_username.grid(row=0, column=1)
        self.entry_password.grid(row=1, column=1)
        tk.Button(master, text="로그인", command=self.try_login).grid(row=2, column=0, columnspan=2)
        tk.Button(master, text="회원가입", command=self.signup).grid(row=3, column=0, columnspan=2)

    def try_login(self):
        username = self.entry_username.get()
        password = self.entry_password.get()
        conn = mysql.connector.connect(**self.dbinfo)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=%s AND password=%s", (username, password))
        row = cursor.fetchone()
        if row:
            self.user_id = row[0]
            self.master.destroy()
        else:
            messagebox.showerror("로그인 실패", "아이디 또는 비밀번호가 틀렸습니다.")
        conn.close()

    def signup(self):
        username = self.entry_username.get()
        password = self.entry_password.get()
        if not username or not password:
            messagebox.showerror("회원가입 실패", "아이디와 비밀번호를 입력하세요.")
            return
        conn = mysql.connector.connect(**self.dbinfo)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()
            messagebox.showinfo("회원가입 성공", "회원가입이 완료되었습니다. 다시 로그인하세요.")
        except mysql.connector.Error as e:
            messagebox.showerror("회원가입 실패", f"에러: {e}")
        conn.close()

class Todo:

    UNCHECKED = "☐ "
    CHECKED = "☑ "

    def __init__(self, root, user_id):
        self.root = root
        self.user_id = user_id
        root.title("To-do List") #맨 위에 제목("To-do List")
        root.geometry("600x600") #사이즈 약간 넓게 조정

        #db세팅
        self.dbinfo = dict(
            host="34.27.84.32",    # 외부 MySQL 서버 주소로 수정!
            user="todo_user",
            password="mypass123",
            database="todo_db"
        )
        try:
            self.conn = mysql.connector.connect(use_pure=True, **self.dbinfo)
        except Exception as err:
            print("❌ MySQL 연결 중 예외 발생:")
            import traceback
            traceback.print_exc()
            from tkinter import messagebox
            messagebox.showerror("DB 연결 실패", str(err))
            raise
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT DATABASE();")
        print(self.cursor.fetchone())

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS todolists (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task VARCHAR(255) NOT NULL,
                completed TINYINT(1) NOT NULL DEFAULT 0,
                sort_order INT NOT NULL DEFAULT 0,
                due_date DATE DEFAULT NULL,
                reminder TINYINT(1) NOT NULL DEFAULT 0
            )
        """)
        
        self.listbox_task_ids = []
        self.deleted_item_stack = []

        self.setup_gui()
        self._ensure_sort_order()
        self.display_tasks()
        self.start_reminder_check_thread()
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        # 입력창
        input_outer_frame = tk.Frame(self.root)
        input_outer_frame.pack(pady = (15, 5))
        
        input_task_frame = tk.Frame(input_outer_frame)
        input_task_frame.pack(pady=2)
        tk.Label(input_task_frame, text="할 일: ").pack(side=tk.LEFT, padx=(0, 5))
        self.task_entry = tk.Entry(input_task_frame, width=40)
        self.task_entry.pack(pady=(15,5))
        self.task_entry.bind("<Return>", self.add_task)
        
        input_due_date_frame = tk.Frame(input_outer_frame)
        input_due_date_frame.pack(pady=2)
        tk.Label(input_due_date_frame, text="마감기한(YYYY-MM-DD): ").pack(side=tk.LEFT, padx=(0,5))
        self.due_date_entry = tk.Entry(input_due_date_frame, width=15)
        self.due_date_entry.pack(side=tk.LEFT)
        self.due_date_entry.bind("<Return>", self.add_task)

        # 버튼 1줄: 추가/삭제/복구/새로고침
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=3)
        self.add_button = tk.Button(button_frame, text="추가", width=8, command=self.add_task)
        self.add_button.pack(side=tk.LEFT, padx=2)
        self.delete_button = tk.Button(button_frame, text="삭제", width=8, command=self.delete_task)
        self.delete_button.pack(side=tk.LEFT, padx=2)
        self.undo_button = tk.Button(button_frame, text="복구", width=8, command=self.undo_delete)
        self.undo_button.pack(side=tk.LEFT, padx=2)
        # 새로고침은 강제 DB 재연결 포함 (우회)
        self.refresh_button = tk.Button(button_frame, text="새로고침", width=8, command=self.force_refresh)
        self.refresh_button.pack(side=tk.LEFT, padx=2)

        # 버튼 2줄: 순서 이동 + 마감기한 설정 + 알림림
        button_frame2 = tk.Frame(self.root)
        button_frame2.pack(pady=3)
        self.up_button = tk.Button(button_frame2, text="↑ 위로", width=8, command=self.move_up)
        self.up_button.pack(side=tk.LEFT, padx=2)
        self.down_button = tk.Button(button_frame2, text="↓ 아래로", width=8, command=self.move_down)
        self.down_button.pack(side=tk.LEFT, padx=2)
        self.set_due_date_button = tk.Button(button_frame2, text="기한변경", width=8, command=self.set_due_date_for_selected)
        self.set_due_date_button.pack(side=tk.LEFT, padx=2)
        self.toggle_reminder_button = tk.Button(button_frame2, text="알림설정", width=8, command=self.toggle_reminder_for_selected)
        self.toggle_reminder_button.pack(side=tk.LEFT, padx=2)

        # 리스트박스
        list_frame = tk.Frame(self.root)
        list_frame.pack(pady=(10,0), padx=10, fill=tk.BOTH, expand=True)
        self.task_listbox = tk.Listbox(self.root, width=50, height=18, selectmode=tk.EXTENDED)
        self.task_listbox.bind('<Double-Button-1>', self.toggle_complete)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.task_listbox.yview)
        self.task_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill="y", in_=list_frame)
        self.task_listbox.pack(side=tk.LEFT, fill="both", expand=True, in_=list_frame)

        # 친구 기능 버튼 프레임 추가
        friend_frame = tk.Frame(self.root)
        friend_frame.pack(pady=3)
        tk.Button(friend_frame, text="친구 요청", width=10, command=self.send_friend_request).pack(side=tk.LEFT, padx=2)
        tk.Button(friend_frame, text="받은 요청확인", width=12, command=self.show_friend_requests).pack(side=tk.LEFT, padx=2)
        tk.Button(friend_frame, text="친구 할일보기", width=12, command=self.show_friend_todos).pack(side=tk.LEFT, padx=2)

    def display_tasks(self):
        self.task_listbox.delete(0, tk.END)
        self.listbox_task_ids.clear()
        try:
            self.cursor.execute("SELECT id, task, completed, due_date, reminder FROM todolists WHERE user_id=%s ORDER BY sort_order ASC, id ASC",(self.user_id,))
            for row_index, row in enumerate(self.cursor.fetchall()):
                task_id, task_text, completed_status, due_date, reminder = row
                prefix = self.CHECKED if completed_status else self.UNCHECKED
                due_date_str = ""
                if due_date:
                    due_date_str = f"(기한: {due_date.strftime('%Y-%m-%d')})"
                reminder_icon = " 🔔" if reminder and not completed_status else ""
                display_text = f"{prefix} {task_text} {due_date_str} {reminder_icon}"
                self.task_listbox.insert(tk.END, display_text)
                self.listbox_task_ids.append(task_id)
                if completed_status:
                    self.task_listbox.itemconfig(tk.END, {'fg': 'gray'})
                elif due_date:
                    today = date.today()
                    if due_date < today:
                        self.task_listbox.itemconfig(tk.END, {'fg': 'darkred'})
                        display_text += "   (기한 지남)"
                    elif due_date == today:
                        self.task_listbox.itemconfig(tk.END, {'fg': 'red'})
                else:
                    self.task_listbox.itemconfig(tk.END, {'fg': 'black'})
        except mysql.connector.Error as e:
            messagebox.showerror("DB 오류", f"할 일 목록을 불러오는 중 오류 발생: {e}")

    def force_refresh(self):
        # 새로고침 시 강제로 DB 연결/커서 다시 열기 (동기화)
        try:
            self.conn.close()
        except:
            pass
        self.conn = mysql.connector.connect(**self.dbinfo)
        self.cursor = self.conn.cursor()
        self.display_tasks()
        self.root.update_idletasks()

    def add_task(self, event=None):
        task = self.task_entry.get()
        due_date_str = self.due_date_entry.get()
        if not task:
            messagebox.showwarning("경고", "할 일을 입력해주세요.")
            return
        
        due_date_obj = None
        if due_date_str.strip():
            try: due_date_obj = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showwarning("경고", "마감기한 형식이 잘못되었습니다. (YYYY-MM-DD)")
                return
        try:
            self.cursor.execute("SELECT IFNULL(MAX(sort_order), 0) FROM todolists WHERE user_id = %s", (self.user_id,))
            max_order = self.cursor.fetchone()[0]
            self.cursor.execute("INSERT INTO todolists (task, sort_order, due_date, user_id) VALUES (%s, %s, %s,%s)", (task, max_order + 1, due_date_obj, self.user_id))
            self.conn.commit()
            print(f"할 일 추가: {task}, 마감기한: {due_date_obj}")
            self.task_entry.delete(0, tk.END)
            self.due_date_entry.delete(0, tk.END)
            self.display_tasks()
        except mysql.connector.Error as e:
            messagebox.showerror("DB 오류", f"할 일 추가 중 오류 발생: {e}")
        
        
    def set_due_date_for_selected(self):
        selected_indices = self.task_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("경고", "마감기한을 변경할 항목을 선택해주세요.")
            return

        # 첫 번째 선택된 항목의 현재 마감기한을 가져와서 다이얼로그 기본값으로 사용 (선택적)
        first_selected_idx = selected_indices[0]
        task_id_to_get_current_due = self.listbox_task_ids[first_selected_idx]
        initial_due_date_str = ""
        try:
            self.cursor.execute("SELECT due_date FROM todolists WHERE id = %s AND user_id = %s", (task_id_to_get_current_due, self.user_id))
            current_due_date_db = self.cursor.fetchone()
            if current_due_date_db and current_due_date_db[0]:
                initial_due_date_str = current_due_date_db[0].strftime('%Y-%m-%d')
        except mysql.connector.Error as e:
            print(f"현재 마감기한 조회 중 오류: {e}") # 오류 발생 시 기본값은 빈 문자열

        # simpledialog를 사용하여 새 마감기한 입력받기
        new_due_date_str = simpledialog.askstring("마감기한 변경",
                                                  "새 마감기한을 입력하세요 (YYYY-MM-DD 형식).\n비우면 마감기한이 제거됩니다.",
                                                  initialvalue=initial_due_date_str)

        if new_due_date_str is None: # 사용자가 '취소'를 누른 경우
            return

        new_due_date_obj = None
        if new_due_date_str.strip(): # 입력값이 있는 경우
            try:
                new_due_date_obj = datetime.strptime(new_due_date_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("오류", "잘못된 날짜 형식입니다. (YYYY-MM-DD)")
                return
        # else: 입력값이 비어있으면 new_due_date_obj는 None으로 유지되어 마감기한 제거

        try:
            for index in selected_indices: # 선택된 모든 항목에 대해 마감기한 업데이트
                task_id_to_update = self.listbox_task_ids[index]
                self.cursor.execute("UPDATE todolists SET due_date = %s WHERE id = %s", (new_due_date_obj, task_id_to_update))
            self.conn.commit()
            self.display_tasks() # 변경사항 반영
        except mysql.connector.Error as e:
            messagebox.showerror("DB 오류", f"마감기한 업데이트 중 오류 발생: {e}")

    def delete_task(self):
        selected_indices = self.task_listbox.curselection()
        if selected_indices:
            for index in sorted(selected_indices, reverse=True):
                task_id = self.listbox_task_ids[index]
                try:
                    self.cursor.execute("SELECT id, task, completed, sort_order, due_date, reminder FROM todolists WHERE id=%s", (task_id,))
                    deleted_row = self.cursor.fetchone()
                    if deleted_row:
                        self.deleted_item_stack.append(deleted_row)
                        self.cursor.execute("DELETE FROM todolists WHERE id=%s AND user_id=%s", (task_id,self.user_id))
                        self.conn.commit()
                except mysql.connector.Error as e:
                    messagebox.showerror("DB 오류", f"할 일 삭제 중 오류 발생: {e}")
            self._reorder_sort_orders()
            self.display_tasks()
        else:
            messagebox.showwarning("경고", "삭제할 항목을 선택해주세요.")

    def undo_delete(self):
        if self.deleted_item_stack:
            last_deleted = self.deleted_item_stack.pop()
            _, task, completed, _, due_date, reminder_stauts = last_deleted
            try:
                self.cursor.execute("SELECT IFNULL(MAX(sort_order), 0) FROM todolists")
                max_order = self.cursor.fetchone()[0]
                self.cursor.execute("INSERT INTO todolists (task, completed, sort_order, due_date, reminder, user_id) VALUES (%s, %s, %s, %s, %s, %s)", (task, completed, max_order + 1, due_date, reminder_stauts, self.user_id))
                self.conn.commit()
                self.display_tasks()
            except mysql.connector.Error as e:
                messagebox.showerror("DB 오류", f"삭제 복구 중 오류 발생: {e}")
        else:
            messagebox.showinfo("안내", "복구할 항목이 없습니다.")

    def toggle_reminder_for_selected(self):
        selected_indices = self.task_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("경고", "알림 설정을 변경할 항목을 선택해주세요.")
            return
        try:
            for index in selected_indices:
                task_id = self.listbox_task_ids[index]
                self.cursor.execute("SELECT reminder FROM todolists WHERE id = %s", (task_id,))
                result = self.cursor.fetchone()
                if result:
                    current_reminder_status = result[0]
                    new_reminder_status = 0 if current_reminder_status else 1
                    self.cursor.execute("UPDATE todolists SET reminder = %s WHERE id = %s", (new_reminder_status, task_id))
            self.conn.commit()
            self.display_tasks()
        except mysql.connector.Error as e:
            messagebox.showerror("DB 오류", f"알림 설정 변경 중 오류 발생: {e}")

    def check_reminders(self):
        #마감기한 내일인 항목 중 알림 설정 된 것 찾아 알림
        while not self.stop_reminder_thread_flag.is_set():
            try:
                if not self.conn or not self.conn.is_connected():
                    print("알림 스레드: DB 연결이 끊어져 재연결 시도")
                    try:
                        print("try진입")
                        self.conn = mysql.connector.connect(**self.dbinfo)
                        print("알림 스레드: DB 재연결 성공")
                    except mysql.connector.Error as db_err:
                        print(f"알림 스레드: DB 재연결 실패-{db_err}")
                        time.sleep(60)
                        continue
                current_date = date.today()
                tomorrow = date.today() + timedelta(days=1)
                query = """
                    SELECT task, due_date FROM todolists
                    WHERE completed = 0 AND reminder = 1 AND due_date = %s
                """
                with self.conn.cursor(dictionary=True) as dict_cursor:
                    dict_cursor.execute(query, (tomorrow,))
                    reminders_for_tomorrow = dict_cursor.fetchall()
                if reminders_for_tomorrow:
                    print(f"알림대상 {len(reminders_for_tomorrow)}개")
                    for task_info in reminders_for_tomorrow:
                        self.root.after(0, self.show_reminder_message, task_info['task'], task_info['due_date'])
            except mysql.connector.Error as e:
                print(f"알림 확인 중 DB 오류: {e}")
                for _ in range(60):
                    if self.stop_reminder_thread_flag.is_set(): break
                    time.sleep(1)
            except Exception as e_global:
                print(f"알림 스레드에서 예기치 않은 오류 발생: {e_global}")
                for _ in range(60):
                    if self.stop_reminder_thread_flag.is_set(): break
                    time.sleep(1)
                    
            for _ in range(3600):
                if self.stop_reminder_thread_flag.is_set(): break
                time.sleep(1)
                
    def show_reminder_message(self, task_name, due_date_val):
        messagebox.showinfo("🔔 마감기한 알림", f"내일 ({due_date_val.strftime('%Y-%m-%d')}) 마감인 {task_name} 잊지 말고 완료하세요!")
        
    def start_reminder_check_thread(self):
        self.stop_reminder_thread_flag = threading.Event()
        self.reminder_thread = threading.Thread(target=self.check_reminders, daemon=True)
        self.reminder_thread.start()
        print("알림 확인 스레드가 시작되었습니다.")
                
    def toggle_complete(self, event=None):
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

    def move_up(self):
        selected = self.task_listbox.curselection()
        if not selected or len(selected) != 1:
            return
        idx = selected[0]
        if idx == 0:
            return
        current_id = self.listbox_task_ids[idx]
        above_id = self.listbox_task_ids[idx - 1]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s AND user_id=%s", (current_id, self.user_id))
        order1 = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s AND user_id=%s", (above_id, self.user_id))
        order2 = self.cursor.fetchone()[0]
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s AND user_id=%s", (order2, current_id, self.user_id))
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s AND user_id=%s", (order1, above_id, self.user_id))

        self.conn.commit()
        self.display_tasks()
        self.task_listbox.selection_clear(0, tk.END)
        self.task_listbox.selection_set(idx - 1)

    def move_down(self):
        selected = self.task_listbox.curselection()
        if not selected or len(selected) != 1:
            return
        idx = selected[0]
        if idx == len(self.listbox_task_ids) - 1:
            return
        current_id = self.listbox_task_ids[idx]
        below_id = self.listbox_task_ids[idx + 1]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s AND user_id=%s", (current_id, self.user_id))
        order1 = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s AND user_id=%s", (below_id, self.user_id))
        order2 = self.cursor.fetchone()[0]
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s AND user_id=%s", (order2, current_id, self.user_id))
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s AND user_id=%s", (order1, below_id, self.user_id))

        self.conn.commit()
        self.display_tasks()
        self.task_listbox.selection_clear(0, tk.END)
        self.task_listbox.selection_set(idx + 1)

    def _reorder_sort_orders(self):
        self.cursor.execute(
            "SELECT id FROM todolists WHERE user_id=%s ORDER BY sort_order ASC, id ASC",
            (self.user_id,)
        )
        rows = self.cursor.fetchall()
        for i, (row_id,) in enumerate(rows):
            self.cursor.execute(
            "UPDATE todolists SET sort_order=%s WHERE id=%s AND user_id=%s",
                (i, row_id, self.user_id)
        )
        self.conn.commit()


    def _ensure_sort_order(self):
        self.cursor.execute(
        "SELECT COUNT(*), SUM(sort_order) FROM todolists WHERE user_id=%s",
        (self.user_id,)
    )
        count, total = self.cursor.fetchone()
        if count > 1 and (total == 0 or total is None):
            self._reorder_sort_orders()


    def on_closing(self):
        if self.conn:
            self.conn.close()
            print("DB 연결이 종료되었습니다.")
        self.root.destroy()
    def send_friend_request(self):
        target_username = simpledialog.askstring("친구 요청", "친구로 추가할 사용자의 아이디를 입력하세요.")
        if not target_username:
            return
        if target_username == self.get_my_username():
            messagebox.showerror("오류", "자기 자신에게는 요청할 수 없습니다.")
            return
        self.cursor.execute("SELECT id FROM users WHERE username=%s", (target_username,))
        row = self.cursor.fetchone()
        if not row:
            messagebox.showerror("오류", "존재하지 않는 사용자입니다.")
            return
        target_id = row[0]
        # 이미 친구인지 체크
        self.cursor.execute(
            "SELECT 1 FROM friend WHERE (user_id=%s AND friend_id=%s) OR (user_id=%s AND friend_id=%s)",
            (self.user_id, target_id, target_id, self.user_id)
        )
        if self.cursor.fetchone():
            messagebox.showinfo("안내", "이미 친구입니다.")
            return
        # 이미 요청했는지 체크
        self.cursor.execute(
            "SELECT 1 FROM friendships WHERE requester_id=%s AND receiver_id=%s AND status='pending'",
            (self.user_id, target_id)
        )
        if self.cursor.fetchone():
            messagebox.showinfo("안내", "이미 요청을 보냈습니다.")
            return
        # 요청 보내기
        self.cursor.execute(
            "INSERT INTO friendships (requester_id, receiver_id, status) VALUES (%s, %s, 'pending')",
            (self.user_id, target_id)
        )
        self.conn.commit()
        messagebox.showinfo("성공", f"{target_username}님에게 친구 요청을 보냈습니다.")
    def get_my_username(self):
        self.cursor.execute("SELECT username FROM users WHERE id=%s", (self.user_id,))
        return self.cursor.fetchone()[0]
    def show_friend_requests(self):
        self.cursor.execute(
            "SELECT f.id, u.username FROM friendships f JOIN users u ON f.requester_id=u.id WHERE f.receiver_id=%s AND f.status='pending'",
            (self.user_id,)
        )
        requests = self.cursor.fetchall()
        if not requests:
            messagebox.showinfo("알림", "받은 친구 요청이 없습니다.")
            return
        req_list = [f"{req_id}: {uname}" for req_id, uname in requests]
        selected = simpledialog.askstring("친구 요청 수락/거절", "수락할 요청 번호를 입력하세요:\n" + "\n".join(req_list))
        if not selected:
            return
        try:
            req_id = int(selected)
        except:
            messagebox.showerror("오류", "잘못된 번호입니다.")
            return
        # 수락/거절 선택
        action = messagebox.askyesno("친구 요청", "수락하시겠습니까? (아니오=거절)")
        if action:
            # 수락
            self.cursor.execute("SELECT requester_id FROM friendships WHERE id=%s", (req_id,))
            row = self.cursor.fetchone()
            if not row:
                messagebox.showerror("오류", "존재하지 않는 요청입니다.")
                return
            requester_id = row[0]
            self.cursor.execute("UPDATE friendships SET status='accepted' WHERE id=%s", (req_id,))
            self.cursor.execute("INSERT INTO friend (user_id, friend_id) VALUES (%s, %s), (%s, %s)",
                                (self.user_id, requester_id, requester_id, self.user_id))
            self.conn.commit()
            messagebox.showinfo("성공", "친구 요청을 수락했습니다.")
        else:
            self.cursor.execute("UPDATE friendships SET status='rejected' WHERE id=%s", (req_id,))
            self.conn.commit()
            messagebox.showinfo("완료", "친구 요청을 거절했습니다.")
    
    def show_friend_todos(self):
        self.cursor.execute(
            "SELECT u.id, u.username FROM friend f JOIN users u ON f.friend_id=u.id WHERE f.user_id=%s",
            (self.user_id,)
        )
        friends = self.cursor.fetchall()
        if not friends:
            messagebox.showinfo("알림", "등록된 친구가 없습니다.")
            return
        friend_map = {str(idx+1): (fid, uname) for idx, (fid, uname) in enumerate(friends)}
        friend_list = [f"{idx}: {uname}" for idx, (fid, uname) in enumerate(friends, 1)]
        selected = simpledialog.askstring("친구 할일 보기", "확인할 친구 번호를 입력하세요:\n" + "\n".join(friend_list))
        if not selected or selected not in friend_map:
            return
        friend_id, friend_name = friend_map[selected]
        self.cursor.execute(
            "SELECT task, completed, due_date FROM todolists WHERE user_id=%s ORDER BY completed ASC, due_date ASC, id ASC",
            (friend_id,)
        )
        todos = self.cursor.fetchall()
        if not todos:
            messagebox.showinfo("친구 할일", f"{friend_name}님의 할 일이 없습니다.")
            return
        msg = "\n".join([f"{'☑' if c else '☐'} {t} {(f'(기한:{d})' if d else '')}" for t, c, d in todos])
        messagebox.showinfo("친구 할일", f"{friend_name}님의 할 일 목록:\n\n{msg}")


if __name__ == '__main__':
    dbinfo = dict(
        host="34.27.84.32",
        user="todo_user",
        password="mypass123",
        database="todo_db"
    )
    login_root = tk.Tk()
    login = LoginWindow(login_root, dbinfo)
    login_root.mainloop()

    if login.user_id:
        root = tk.Tk()
        try:
            app = Todo(root, login.user_id)
            root.mainloop()
        except Exception as e:
            print(f"앱 실행 중 오류 발생 : {e}")
            traceback.print_exc()
            sys.exit(1)
