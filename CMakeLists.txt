cmake_minimum_required(VERSION 3.15)
project(matmul CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()
if(NOT MSVC)
    set(CMAKE_CXX_FLAGS_RELEASE "-O2")
endif()

find_package(Threads REQUIRED)
add_executable(matmul src/matmul.cpp)
target_link_libraries(matmul Threads::Threads)
if(MINGW)
    target_link_options(matmul PRIVATE -static)
endif()
