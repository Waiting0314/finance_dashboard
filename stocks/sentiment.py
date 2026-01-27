"""
情緒分析模組
使用 Hugging Face Transformers 進行新聞標題情緒分析（GPU 加速）
"""
import torch
from functools import lru_cache

# 全域變數：延遲載入模型
_sentiment_pipeline = None

def _load_sentiment_model():
    """延遲載入情緒分析模型，確保 GPU 可用時使用 GPU"""
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        try:
            from transformers import pipeline
            
            # 檢查 GPU 是否可用
            device = 0 if torch.cuda.is_available() else -1
            if torch.cuda.is_available():
                print(f"[Sentiment] 使用 GPU: {torch.cuda.get_device_name(0)}")
            else:
                print("[Sentiment] GPU 不可用，使用 CPU")
            
            # 使用多語言情緒分析模型（支援中英文）
            _sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="lxyuan/distilbert-base-multilingual-cased-sentiments-student",
                device=device,
                truncation=True,
                max_length=512
            )
            print("[Sentiment] 模型載入成功")
        except Exception as e:
            print(f"[Sentiment] 模型載入失敗: {e}")
            _sentiment_pipeline = None
    return _sentiment_pipeline


def analyze_sentiment(text: str) -> str:
    """
    分析文字情緒
    
    Args:
        text: 要分析的文字（新聞標題）
    
    Returns:
        'positive', 'negative', 或 'neutral'
    """
    if not text or len(text.strip()) == 0:
        return 'neutral'
    
    try:
        pipeline = _load_sentiment_model()
        if pipeline is None:
            return 'neutral'
        
        result = pipeline(text[:512])[0]  # 限制長度避免記憶體問題
        label = result['label'].lower()
        score = result['score']
        
        # 信心度閾值：低於 0.6 視為中性
        if score < 0.6:
            return 'neutral'
        
        # 標準化標籤
        if 'positive' in label:
            return 'positive'
        elif 'negative' in label:
            return 'negative'
        else:
            return 'neutral'
            
    except Exception as e:
        print(f"[Sentiment] 分析錯誤: {e}")
        return 'neutral'


def analyze_batch(texts: list) -> list:
    """
    批次分析多個文字的情緒
    
    Args:
        texts: 文字列表
    
    Returns:
        情緒標籤列表
    """
    if not texts:
        return []
    
    try:
        pipeline = _load_sentiment_model()
        if pipeline is None:
            return ['neutral'] * len(texts)
        
        # 預處理：截斷過長文字
        processed_texts = [t[:512] if t else "" for t in texts]
        results = pipeline(processed_texts)
        
        sentiments = []
        for result in results:
            label = result['label'].lower()
            score = result['score']
            
            if score < 0.6:
                sentiments.append('neutral')
            elif 'positive' in label:
                sentiments.append('positive')
            elif 'negative' in label:
                sentiments.append('negative')
            else:
                sentiments.append('neutral')
        
        return sentiments
        
    except Exception as e:
        print(f"[Sentiment] 批次分析錯誤: {e}")
        return ['neutral'] * len(texts)


def unload_model():
    """釋放 GPU 記憶體"""
    global _sentiment_pipeline
    if _sentiment_pipeline is not None:
        del _sentiment_pipeline
        _sentiment_pipeline = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("[Sentiment] 模型已卸載，GPU 記憶體已釋放")


def check_gpu_available() -> dict:
    """
    檢查 GPU 狀態
    
    Returns:
        dict 包含 GPU 資訊
    """
    info = {
        'cuda_available': torch.cuda.is_available(),
        'device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
        'device_name': None,
        'memory_allocated': None,
        'memory_reserved': None
    }
    
    if info['cuda_available'] and info['device_count'] > 0:
        info['device_name'] = torch.cuda.get_device_name(0)
        info['memory_allocated'] = f"{torch.cuda.memory_allocated(0) / 1024**2:.2f} MB"
        info['memory_reserved'] = f"{torch.cuda.memory_reserved(0) / 1024**2:.2f} MB"
    
    return info
