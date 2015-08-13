import random
import string

def generate_random_key():
    lowerChars = string.ascii_letters.lower()
    upperChars = lowerChars.upper()
    digits = string.digits
    groups = [
        {
            "chars": lowerChars,
            "num": 3
        },
        {
            "chars": upperChars,
            "num": 2
        },
        {
            "chars": lowerChars,
            "num": 5
        },
        {
            "chars": digits,
            "num": 2
        }
    ]
    # make a longer password
    # new comment
    groups = groups + groups
    random.shuffle(groups)

    random_gen = random.SystemRandom()
    random_key = ""
    for group in groups:
        part = '' . join(random_gen.choice(group["chars"]) for i in range(group["num"]))
        random_key += part

    return random_key

if __name__=='__main__':
    print '\nRandom Secret Key: \n', generate_random_key(), '\n'