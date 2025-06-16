class TestClass {
public:
    TestClass() : _tcpStream(new TCP_streambuf(4096, -1, this)) {
        // Some initialization
    }
    
    ~TestClass() {
        // Need to fix this line
        // Some other cleanup
    }
    
    void someMethod() {
        // Other code
    }
};