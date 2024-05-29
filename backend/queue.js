class MutationTaskExecutor {
    constructor() {
        this.queue = [];
        this.isProcessing = false;
    }

    async mutation(email, task) {
        const id = Math.random().toString(36).substring(7);
        console.log('mutation', id, email)
        return new Promise(async resolve => {
            console.log('add task to queue', id)
            this.queue.push({ task, id, resolve });
            if (!this.isProcessing) {
                await this.processQueue();
            }
        });
    }

    async processQueue() {
        console.log('start processing queue')
        this.isProcessing = true;
        while (this.queue.length > 0) {
            const { task, id, resolve } = this.queue.shift();
            await task();
            console.log('resolving', id)
            resolve();
        }
        this.isProcessing = false;
    }
}

exports.cqrs = new MutationTaskExecutor();
