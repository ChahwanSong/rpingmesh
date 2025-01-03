#pragma once

#include <cstdarg>  // va_list, va_start, va_end
#include <cstring>  // strerror
#include <iostream>
#include <sstream>

#include "extlibs.hpp"
#include "macro.hpp"

// spdlog
const int LOG_FILE_SIZE = 30 * 1024 * 1024;  // 30 MB
const int LOG_FILE_EXTRA_NUM = 0;            // extra rotate-log files
const std::string LOG_FORMAT = "[%Y-%m-%d %H:%M:%S.%f][%l] %v";
const std::string LOG_RESULT_FORMAT = "%v";
const enum spdlog::level::level_enum LOG_LEVEL_SERVER = spdlog::level::info;
const enum spdlog::level::level_enum LOG_LEVEL_CLIENT = spdlog::level::info;
const enum spdlog::level::level_enum LOG_LEVEL_RESULT = spdlog::level::info;
const enum spdlog::level::level_enum LOG_LEVEL_PING_TABLE = spdlog::level::info;

inline std::shared_ptr<spdlog::logger> initialize_logger(
    const std::string &logname, const std::string &dir_path,
    enum spdlog::level::level_enum log_level, int file_size, int file_num) {
    auto logger = spdlog::get(logname);
    if (!logger) {
        logger = spdlog::rotating_logger_mt(
            logname, get_source_directory() + dir_path + "/" + logname + ".log",
            file_size, file_num);
        logger->set_pattern(LOG_FORMAT);
        logger->set_level(log_level);
        logger->flush_on(log_level);
        logger->info("Logger initialization (logname: {}, PID: {})", logname,
                     getpid());
    }
    return logger;
}