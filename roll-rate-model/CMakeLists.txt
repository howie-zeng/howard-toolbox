cmake_minimum_required(VERSION 3.16)
project(roll_rate_model VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# --- Options ---
option(BUILD_TESTS "Build unit tests" ON)
option(BUILD_PYTHON "Build Python bindings" OFF)

# --- OpenMP ---
find_package(OpenMP)
if(OpenMP_CXX_FOUND)
    message(STATUS "OpenMP found: ${OpenMP_CXX_VERSION}")
endif()

# --- Core library ---
file(GLOB_RECURSE LIB_SOURCES
    src/model/*.cpp
    src/runners/*.cpp
    src/utils/*.cpp
    src/*.cpp
)

add_library(simengine ${LIB_SOURCES})
target_include_directories(simengine PUBLIC include)
if(OpenMP_CXX_FOUND)
    target_link_libraries(simengine PUBLIC OpenMP::OpenMP_CXX)
endif()

# --- Main executable ---
add_executable(sim_main src/main.cpp)
target_link_libraries(sim_main PRIVATE simengine)

# --- Debug calc ---
add_executable(debug_calc src/debug_calc.cpp)
target_link_libraries(debug_calc PRIVATE simengine)

# --- Tests ---
if(BUILD_TESTS)
    include(FetchContent)
    FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG v1.14.0
    )
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)

    enable_testing()

    file(GLOB_RECURSE TEST_SOURCES tests/*.cpp)
    if(TEST_SOURCES)
        add_executable(tests ${TEST_SOURCES})
        target_link_libraries(tests PRIVATE simengine GTest::gtest_main)
        include(GoogleTest)
        gtest_discover_tests(tests)
    endif()
endif()

# --- Python bindings (optional) ---
if(BUILD_PYTHON)
    find_package(pybind11 CONFIG)
    if(pybind11_FOUND)
        pybind11_add_module(_simengine python/simengine/_bindings.cpp)
        target_link_libraries(_simengine PRIVATE simengine)
    else()
        message(WARNING "pybind11 not found — skipping Python bindings")
    endif()
endif()
