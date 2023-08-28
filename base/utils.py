
import random
import string

def generate_random_string(length):
    letters = string.ascii_letters  # Includes both lowercase and uppercase alphabets
    return "".join(random.choice(letters) for _ in range(length))



def add_fees(amount):
    if amount >= 100:
        return amount * 0.1
    elif amount < 100:
        return amount * 0.05
    return


