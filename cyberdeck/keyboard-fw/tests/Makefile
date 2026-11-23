# Host tests for the hardware-free parts of the firmware.
SRC = ../src/proto.c ../src/keymap.c ../src/motion.c ../src/ui.c
CFLAGS = -std=c11 -Wall -Wextra -Werror -O1 -I../src

run: test_host
	./test_host

test_host: test_host.c $(SRC)
	$(CC) $(CFLAGS) -o $@ test_host.c $(SRC) -lm

frames: frames.c ../src/proto.c ../src/keymap.c
	$(CC) $(CFLAGS) -o $@ frames.c ../src/proto.c ../src/keymap.c

clean:
	rm -f test_host frames *.pgm
