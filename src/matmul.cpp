#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <string>
#include <thread>
#include <vector>

using i64 = std::int64_t;
using Clock = std::chrono::steady_clock;

struct Matrix {
    int rows, cols;
    std::vector<i64> d;
    Matrix(int r, int c) : rows(r), cols(c), d((size_t)r * c, 0) {}
    i64& at(int i, int j) { return d[(size_t)i * cols + j]; }
    const i64& at(int i, int j) const { return d[(size_t)i * cols + j]; }
};

static void fill_random(Matrix& M, std::mt19937_64& rng) {
    std::uniform_int_distribution<int> dist(0, 9);
    for (auto& x : M.d) x = dist(rng);
}

static std::atomic<long long> rows_done{0};

static void row_itj(const Matrix& A, const Matrix& B, Matrix& C, int i) {
    const int m = A.cols, k = B.cols;
    i64* c = &C.d[(size_t)i * k];
    for (int t = 0; t < m; ++t) {
        const i64 a = A.d[(size_t)i * m + t];
        const i64* b = &B.d[(size_t)t * k];
        for (int j = 0; j < k; ++j) c[j] += a * b[j];
    }
}

static void row_ijt(const Matrix& A, const Matrix& B, Matrix& C, int i) {
    const int m = A.cols, k = B.cols;
    for (int j = 0; j < k; ++j) {
        i64 s = 0;
        for (int t = 0; t < m; ++t) s += A.d[(size_t)i * m + t] * B.d[(size_t)t * k + j];
        C.d[(size_t)i * k + j] = s;
    }
}

static void worker(const Matrix& A, const Matrix& B, Matrix& C, int lo, int hi, bool itj) {
    for (int i = lo; i < hi; ++i) {
        if (itj) row_itj(A, B, C, i); else row_ijt(A, B, C, i);
        rows_done.fetch_add(1, std::memory_order_relaxed);
    }
}

int main(int argc, char** argv) {
    if (argc < 5) {
        std::fprintf(stderr, "Использование: %s n m k T [itj|ijt] [прогресс 1|0]\n", argv[0]);
        return 1;
    }
    int n = std::atoi(argv[1]), m = std::atoi(argv[2]), k = std::atoi(argv[3]);
    int T = std::atoi(argv[4]);
    bool itj = !(argc > 5 && std::strcmp(argv[5], "ijt") == 0);
    bool show_progress = !(argc > 6 && std::strcmp(argv[6], "0") == 0);
    if (n < 1 || m < 1 || k < 1 || T < 1) { std::fprintf(stderr, "Параметры должны быть >= 1\n"); return 1; }

    std::mt19937_64 rng(42);
    Matrix A(n, m), B(m, k), C(n, k);
    fill_random(A, rng);
    fill_random(B, rng);

    std::vector<std::thread> threads;
    threads.reserve(T);
    rows_done = 0;
    int base = n / T, rem = n % T;

    auto t0 = Clock::now();
    int lo = 0;
    for (int p = 0; p < T; ++p) {
        int cnt = base + (p < rem ? 1 : 0);
        threads.emplace_back(worker, std::cref(A), std::cref(B), std::ref(C), lo, lo + cnt, itj);
        lo += cnt;
    }

    if (show_progress) {
        int last = -1;
        while (true) {
            long long d = rows_done.load();
            int pct = (int)(d * 100 / n);
            if (pct != last) { std::printf("\rПрогресс: %d%%", pct); std::fflush(stdout); last = pct; }
            if (d >= n) break;
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
        }
        std::printf("\n");
    }
    for (auto& th : threads) th.join();
    auto t1 = Clock::now();
    double sec = std::chrono::duration<double>(t1 - t0).count();

    i64 checksum = 0;
    for (i64 x : C.d) checksum += x;
    i64 expected = 0;
    for (int t = 0; t < m; ++t) {
        i64 ca = 0, rb = 0;
        for (int i = 0; i < n; ++i) ca += A.at(i, t);
        for (int j = 0; j < k; ++j) rb += B.at(t, j);
        expected += ca * rb;
    }

    if (n <= 10 && k <= 10) {
        std::printf("Матрица C:\n");
        for (int i = 0; i < n; ++i) { for (int j = 0; j < k; ++j) std::printf("%6lld", (long long)C.at(i, j)); std::printf("\n"); }
    }
    std::printf("Время умножения: %.6f с\n", sec);
    std::printf("Контрольная сумма: %lld (ожидалось %lld) -> %s\n",
                (long long)checksum, (long long)expected, checksum == expected ? "OK" : "ОШИБКА");
    std::printf("RESULT %d %d %d %d %s %.6f %lld\n", n, m, k, T, itj ? "itj" : "ijt", sec, (long long)checksum);
    return checksum == expected ? 0 : 2;
}
