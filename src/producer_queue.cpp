#include "producer_queue.hpp"

// Constructor: Acquire shared memory
ProducerQueue::ProducerQueue(const std::string& shm_name)
    : shm_name(shm_name), messages_in_batch(0) {
    initSharedMemory();
    last_flush_time =
        std::chrono::steady_clock::now();  // Initialize last message time
    spdlog::get("producer_queue")
        ->info("[{}] Producer queue is created\n", this->shm_name.c_str());
}

// Initialize and map shared memory
void ProducerQueue::initSharedMemory() {
    // Create shared memory object
    shm_fd = shm_open(shm_name.c_str(), O_CREAT | O_RDWR, 0666);
    if (shm_fd == -1) {
        spdlog::get("producer_queue")
            ->error("[{}}] Failed to create shared memory\n",
                    this->shm_name.c_str());
        throw std::runtime_error("Failed to create shared memory");
    }

    // Set the size of the shared memory object
    if (ftruncate(shm_fd, sizeof(SharedData)) == -1) {
        close(shm_fd);
        shm_unlink(shm_name.c_str());
        spdlog::get("producer_queue")
            ->error("[{}}] Failed to set the size of shared memory\n",
                    this->shm_name.c_str());
        throw std::runtime_error("Failed to set the size of shared memory");
    }

    // Map the shared memory object into the process's address space
    data = static_cast<SharedData*>(mmap(
        0, sizeof(SharedData), PROT_WRITE | PROT_READ, MAP_SHARED, shm_fd, 0));
    if (data == MAP_FAILED) {
        close(shm_fd);
        shm_unlink(shm_name.c_str());
        spdlog::get("producer_queue")
            ->error("[{}}] Failed to map shared memory\n",
                    this->shm_name.c_str());
        throw std::runtime_error("Failed to map shared memory");
    }

    // Initialize the shared data
    data->head.store(0);
    data->tail.store(0);
    data->message_ready.store(false);
}

// Destructor: Release shared memory (RAII)
ProducerQueue::~ProducerQueue() {
    flushBatch();  // Flush remaining messages before cleanup
    if (data) {
        munmap(data, sizeof(SharedData));
    }
    if (shm_fd != -1) {
        close(shm_fd);
        shm_unlink(shm_name.c_str());
    }
}

// Write a message to the shared memory queue
bool ProducerQueue::writeMessage(const std::string& message) {
    int next_tail = (data->tail.load() + 1) % BUFFER_SIZE;

    if (next_tail == data->head.load()) {
        return false;  // Queue is full
    }

    std::strncpy(data->messages[data->tail], message.c_str(), MESSAGE_SIZE - 1);
    data->tail.store(next_tail);
    return true;
}
// Send a message and handle batch processing
bool ProducerQueue::sendMessage(const std::string& message) {
    if (!writeMessage(message)) {
        ++n_dropped_msgs;
        printf("dropped: %lu\n", n_dropped_msgs);
        return false;
    }

    messages_in_batch++;
    auto now = std::chrono::steady_clock::now();

    // calculate a timeout
    auto time_elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                            now - last_flush_time)
                            .count();

    // if > batch size or timeout, then flush
    if (messages_in_batch >= BATCH_SIZE || time_elapsed >= BATCH_TIMEOUT_MS) {
        flushBatch();
    }

    return true;
}

// Flush batch of messages to consumer
void ProducerQueue::flushBatch() {
    if (messages_in_batch > 0) {
        data->message_ready.store(true);
        while (data->message_ready.load()) {
            std::this_thread::sleep_for(std::chrono::microseconds(500));
        }
        messages_in_batch = 0;
        last_flush_time = std::chrono::steady_clock::now();
    }
}

std::chrono::time_point<std::chrono::steady_clock>
ProducerQueue::getLastFlushTime() {
    return last_flush_time;
}

uint64_t ProducerQueue::getNumDroppedMsgs() { return n_dropped_msgs; }