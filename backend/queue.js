class MutationTaskExecutor {
    constructor() {
        this.queue = [];
        this.isProcessing = false;
    }

    async mutation(task) {
        this.queue.push(task);
        if (!this.isProcessing) {
            await this.processQueue();
        }
    }

    async processQueue() {
        this.isProcessing = true;
        while (this.queue.length > 0) {
            const task = this.queue.shift();
            await task();
        }
        this.isProcessing = false;
    }
}

exports.cqrs = new MutationTaskExecutor();
