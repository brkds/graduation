#ifndef ANALYSIS_CONFIG_H
#define ANALYSIS_CONFIG_H

// 分析遍数枚举
enum class AnalysisPass {
    FIRST_PASS,   // 第一遍：收集定义（全局变量、函数）
    SECOND_PASS   // 第二遍：分析关系（访问、调用、指针）
};

// 分析配置结构体
struct AnalysisConfig {
    bool enableCallAnalysis = false;
    bool singleThreadMode = false;
    bool twoPassAnalysis = true;  // 默认启用两遍分析
    AnalysisPass currentPass = AnalysisPass::FIRST_PASS;
};

#endif // ANALYSIS_CONFIG_H
