cmake_minimum_required(VERSION 4.3)
project(cache_lab)

set(CMAKE_CXX_STANDARD 20)

add_executable(cache_lab
        src/main.cpp
        src/cli.cpp
        src/cli.hpp
        src/cache_config.cpp
        src/cache.cpp
        src/trace.cpp
        src/trace.hpp
        src/access.hpp
        src/address.hpp
        src/cache.hpp
        src/cache_config.hpp
)
