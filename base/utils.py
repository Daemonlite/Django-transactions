
import random
import string


def generate_random_string(length):
    letters = string.ascii_letters  # Includes both lowercase and uppercase alphabets
    return "".join(random.choice(letters) for _ in range(length))


from post_office import mail

def send_receipient_email(recipient,message):
    mail.send(
        recipient,  
        'noreply@bitly.com',
        subject='Transaction Notice',
        message=message,
        html_message=' <p>Hi,there you have received your funds kindle check your wallet/p>!',
    )


def send_sender_email(sender,message):
    mail.send(
        sender,  
        'noreply@bitly.com',
        subject='Transaction Notice',
        message=message,
        html_message=' <p>Hi,there you have successfully sent your funds</p>!',
    )

