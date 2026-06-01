import poplib
from email import parser

# Server Configuration
POP3_SERVER = '192.168.1.1'
USER = 'admin1@example.com'
PASSWORD = '123'

def fetch_latest_email():
    try:
        # 1. Connect to the server (Use POP3_SSL for port 995)
        server = poplib.POP3_SSL(POP3_SERVER, 995)
        
        # 2. Authentication (USER/PASS commands)
        server.user(USER)
        server.pass_(PASSWORD)
        
        # 3. Get mailbox status (STAT command)
        # Returns (message count, total mailbox size)
        msg_count, size = server.stat()
        print(f"Messages: {msg_count}, Total Size: {size} bytes")

        if msg_count > 0:
            # 4. Retrieve the latest message (RETR command)
            # Lines are returned as a list of bytes
            resp, lines, octets = server.retr(msg_count)
            
            # Join bytes and parse into an email object
            msg_content = b'\n'.join(lines).decode('utf-8')
            msg = parser.Parser().parsestr(msg_content)
            
            print("--- Latest Email ---")
            print(f"From: {msg['From']}")
            print(f"Subject: {msg['Subject']}")
            
            # Optional: Mark for deletion (DELE command)
            # server.dele(msg_count)

        # 5. Commit changes and disconnect (QUIT command)
        server.quit()
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    fetch_latest_email()