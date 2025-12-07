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
    
    // For manual JSON serialization
    string toJson(bool suspicious, const string& reason) const {
        stringstream ss;
        ss << "{";
        ss << "\"id\": \"" << id << "\", ";
        ss << "\"amount\": " << amount << ", ";
        ss << "\"description\": \"" << description << "\", ";
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

// --- Algorithm 2: KMP Algorithm ---

// Function to compute the LPS (Longest Prefix Suffix) array
vector<int> computeLPSArray(const string& pattern) {
    int m = pattern.length();
    vector<int> lps(m);
    int len = 0;
    lps[0] = 0;
    int i = 1;

    while (i < m) {
        if (pattern[i] == pattern[len]) {
            len++;
            lps[i] = len;
            i++;
        } else {
            if (len != 0) {
                len = lps[len - 1];
            } else {
                lps[i] = 0;
                i++;
            }
        }
    }
    return lps;
}

// KMP Search function
bool KMPSearch(const string& pattern, const string& text) {
    int m = pattern.length();
    int n = text.length();
    
    if (m == 0) return false;
    
    vector<int> lps = computeLPSArray(pattern);
    int i = 0; // index for text
    int j = 0; // index for pattern

    string lowerText = text;
    string lowerPattern = pattern;
    // Case insensitive comparison basics
    transform(lowerText.begin(), lowerText.end(), lowerText.begin(), ::tolower);
    transform(lowerPattern.begin(), lowerPattern.end(), lowerPattern.begin(), ::tolower);

    while (i < n) {
        if (lowerPattern[j] == lowerText[i]) {
            j++;
            i++;
        }

        if (j == m) {
            return true; // Pattern found
        } else if (i < n && lowerPattern[j] != lowerText[i]) {
            if (j != 0)
                j = lps[j - 1];
            else
                i = i + 1;
        }
    }
    return false;
}

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
    
    // Simple CSV parser: ID,Amount,Description
    while (getline(cin, line)) {
        if (line.empty()) continue;
        
        stringstream ss(line);
        string segment;
        vector<string> parts;
        
        while(getline(ss, segment, ',')) {
            parts.push_back(segment);
        }
        
        if (parts.size() >= 3) {
            Transaction t;
            t.id = parts[0];
            try {
                t.amount = stod(parts[1]);
            } catch (...) {
                t.amount = 0.0;
            }
            // Description might contain commas, so we should join the rest if split, 
            // but for simple CSV assumption we take 3rd part. 
            // Ideally handle real CSV but this assumes simple format.
            t.description = parts[2];
            for (size_t i = 3; i < parts.size(); ++i) {
                t.description += "," + parts[i];
            }
            
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
        // Note: The prompt says "If an ID appears more than 3 times".
        // This means if total count > 3, ALL transactions for that ID are suspicious?
        // Or just the 4th onwards? "flag all its transactions" -> ALL.
        if (!suspicious && frequencyMap[t.id] > 3) {
            suspicious = true;
            reason = "High Frequency Fraud (Hashing)";
        }

        // Check 3: Keywords (KMP)
        if (!suspicious) {
            if (KMPSearch("crypto", t.description)) {
                suspicious = true;
                reason = "KMP Match: 'crypto'";
            } else if (KMPSearch("offshore", t.description)) {
                suspicious = true;
                reason = "KMP Match: 'offshore'";
            } else if (KMPSearch("bet", t.description)) {
                suspicious = true;
                reason = "KMP Match: 'bet'";
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
