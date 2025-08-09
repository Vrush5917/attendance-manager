CC = gcc
CFLAGS = -O2 -fPIC -Wall
TARGET = libattendance.so
SRC = attendance.c

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -shared -o $(TARGET) $(SRC)

clean:
	rm -f $(TARGET)