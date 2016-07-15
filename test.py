rgbs = [(1,2,3),(4,5,6)]
colorwidth = 54
for i in range(colorwidth):
    for rgb in rgbs:
        for j in range(colorwidth):
            for val in rgb:
                print(val, end = " ")
            print()
