#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <unordered_map>
#include <algorithm>

using namespace std;

// --- Data Structures ---

struct Transaction {
    string id;
    double amount;
    string description;
    string time;
    string payment_mode;
    
    // For manual JSON serialization
    string toJson(bool suspicious, const string& reason) const {
        stringstream ss;
        ss << "{";
        ss << "\"id\": \"" << id << "\", ";
        ss << "\"amount\": " << amount << ", ";
        ss << "\"description\": \"" << description << "\", ";
        ss << "\"time\": \"" << time << "\", ";
        ss << "\"payment_mode\": \"" << payment_mode << "\", ";
        ss << "\"is_suspicious\": " << (suspicious ? "true" : "false") << ", ";
        ss << "\"reason\": \"" << reason << "\"";
        ss << "}";
        return ss.str();
    }
};

// --- Algorithm 3: Trie for Blacklist ---

class TrieNode {
public:
    unordered_map<char, TrieNode*> children;
    bool isEndOfWord;

    TrieNode() : isEndOfWord(false) {}
};

class Trie {
    TrieNode* root;

    void deleteNodes(TrieNode* node) {
        if (!node) return;
        for (auto& pair : node->children) {
            deleteNodes(pair.second);
        }
        delete node;
    }

public:
    Trie() {
        root = new TrieNode();
    }
    
    ~Trie() {
        deleteNodes(root);
    }

    void insert(const string& word) {
        TrieNode* current = root;
        for (char ch : word) {
            if (current->children.find(ch) == current->children.end()) {
                current->children[ch] = new TrieNode();
            }
            current = current->children[ch];
        }
        current->isEndOfWord = true;
    }

    bool search(const string& word) {
        TrieNode* current = root;
        for (char ch : word) {
            if (current->children.find(ch) == current->children.end()) {
                return false;
            }
            current = current->children[ch];
        }
        return current != nullptr && current->isEndOfWord;
    }
};

// --- Algorithm 2: Boyer-Moore Algorithm ---

class BoyerMoore {
public:
    static void badCharHeuristic(const string& str, int size, int badchar[256]) {
        for (int i = 0; i < 256; i++)
            badchar[i] = -1;
        for (int i = 0; i < size; i++)
            badchar[(int)str[i]] = i;
    }

    static bool search(const string& pat, const string& txt) {
        int m = pat.size();
        int n = txt.size();
        int badchar[256];

        badCharHeuristic(pat, m, badchar);

        int s = 0; 
        while (s <= (n - m)) {
            int j = m - 1;
            while (j >= 0 && pat[j] == txt[s + j])
                j--;

            if (j < 0) {
                return true; // Pattern found
            } else {
                s += max(1, j - badchar[(int)txt[s + j]]);
            }
        }
        return false;
    }
};

// --- Algorithm 3: Rabin-Karp Algorithm ---

class RabinKarp {
public:
    static bool search(const string& pat, const string& txt, int q = 101) {
        int M = pat.length();
        int N = txt.length();
        int i, j;
        int p = 0; // hash value for pattern
        int t = 0; // hash value for txt
        int h = 1;
        int d = 256; // number of characters in the input alphabet

        if (M > N) return false;

        for (i = 0; i < M - 1; i++)
            h = (h * d) % q;

        for (i = 0; i < M; i++) {
            p = (d * p + pat[i]) % q;
            t = (d * t + txt[i]) % q;
        }

        for (i = 0; i <= N - M; i++) {
            if (p == t) {
                for (j = 0; j < M; j++) {
                    if (txt[i + j] != pat[j])
                        break;
                }
                if (j == M)
                    return true;
            }
            if (i < N - M) {
                t = (d * (t - txt[i] * h) + txt[i + M]) % q;
                if (t < 0)
                    t = (t + q);
            }
        }
        return false;
    }
};

// --- Main Engine ---

int main() {
    // 1. Setup Blacklist (Trie)
    Trie blacklist;
    blacklist.insert("9999");
    blacklist.insert("1001");
    // Add more blacklist IDs as needed

    // 2. Setup Frequency Map (Hashing)
    unordered_map<string, int> frequencyMap;

    // 3. Read Transactions
    vector<Transaction> transactions;
    string line;
    
            // Simple CSV parser: ID,Amount,Description,Time,PaymentMode
        while (getline(cin, line)) {
            if (line.empty()) continue;
            
            stringstream ss(line);
            string segment;
            vector<string> parts;
            
            while(getline(ss, segment, ',')) {
                parts.push_back(segment);
            }
            
            // We now expect at least 3, ideally 5. If < 5, we fill with defaults.
            if (parts.size() >= 3) {
                Transaction t;
                t.id = parts[0];
                try {
                    t.amount = stod(parts[1]);
                } catch (...) {
                    t.amount = 0.0;
                }
                t.description = parts[2];
                
                // Handle optional extra columns if present
                if (parts.size() >= 4) t.time = parts[3];
                else t.time = "00:00";
                
                if (parts.size() >= 5) t.payment_mode = parts[4];
                else t.payment_mode = "unknown";
    
                // If description was split by comma (and we didn't have 5 columns explicitly), 
                // logic gets messy. For this system, we assume the Pre-Processor (Python) 
                // guarantees the format or we accept simple CSV rules.
                // Let's stick to: If > 5 parts, the rest are ignored or part of description?
                // To be safe, let's assume the Python script normalizes the input to exactly 5 columns.
                
                transactions.push_back(t);
                frequencyMap[t.id]++;
            }
        }
    // 4. Analyze and Output JSON
    cout << "[";
    for (size_t i = 0; i < transactions.size(); ++i) {
        const auto& t = transactions[i];
        bool suspicious = false;
        string reason = "";

        // Check 1: Blacklist (Trie)
        if (blacklist.search(t.id)) {
            suspicious = true;
            reason = "Blacklisted ID (Trie Match)";
        }
        
        // Check 2: High Frequency (Hashing)
        if (!suspicious && frequencyMap[t.id] > 3) {
            suspicious = true;
            reason = "High Frequency Fraud (Hashing)";
        }

        // Check 3: Keywords (Boyer-Moore & Rabin-Karp)
        if (!suspicious) {
            // Case insensitive preprocessing
            string lowerDesc = t.description;
            transform(lowerDesc.begin(), lowerDesc.end(), lowerDesc.begin(), ::tolower);

            // Boyer-Moore for keyword matches
            if (BoyerMoore::search("crypto", lowerDesc)) {
                suspicious = true;
                reason = "Boyer-Moore Match: 'crypto'";
            } else if (BoyerMoore::search("offshore", lowerDesc)) {
                suspicious = true;
                reason = "Boyer-Moore Match: 'offshore'";
            } else if (BoyerMoore::search("gambling", lowerDesc)) {
                suspicious = true;
                reason = "Boyer-Moore Match: 'gambling'";
            } else if (BoyerMoore::search("swiss", lowerDesc)) {
                suspicious = true;
                reason = "Boyer-Moore Match: 'swiss'";
            } else if (BoyerMoore::search("fantasy", lowerDesc)) {
                suspicious = true;
                reason = "Boyer-Moore Match: 'fantasy'";
            } else if (BoyerMoore::search("stocks", lowerDesc)) {
                suspicious = true;
                reason = "Boyer-Moore Match: 'stocks'";
            } else if (BoyerMoore::search("intraday", lowerDesc)) {
                suspicious = true;
                reason = "Boyer-Moore Match: 'intraday'";
            } else if (BoyerMoore::search("trading", lowerDesc)) {
                suspicious = true;
                reason = "Boyer-Moore Match: 'trading'";
            }
            // Rabin-Karp for shorter/specific keywords
            else if (RabinKarp::search("bet", lowerDesc)) {
                suspicious = true;
                reason = "Rabin-Karp Match: 'bet'";
            } else if (RabinKarp::search("stake", lowerDesc)) {
                suspicious = true;
                reason = "Rabin-Karp Match: 'stake'";
            } else if (RabinKarp::search("forex", lowerDesc)) {
                suspicious = true;
                reason = "Rabin-Karp Match: 'forex'";
            }
        }

        cout << t.toJson(suspicious, reason);
        if (i < transactions.size() - 1) {
            cout << ",";
        }
    }
    cout << "]" << endl;

    return 0;
}
