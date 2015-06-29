
OPENCV_LIBS=-lopencv_highgui -lopencv_core

all: test run

run: test
	@echo '------------------------------------------------'
	./test

test.o: test.cpp
	g++ -pipe test.cpp -o test.o -c -std=c++11 -Wall

test: test.o
	g++ -pipe test.o -o test -std=c++11 -Wall $(OPENCV_LIBS)

clean:
	rm -f test.o test
