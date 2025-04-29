import numpy as np
import torch
import pickle
from transformers import AutoTokenizer, AutoModel
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from sklearn.metrics.pairwise import cosine_similarity

# Define BERT model and tokenizer
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Initialize tokenizer and model (lazy-loaded on first use)
_tokenizer = None
_model = None

def get_tokenizer():
    """Lazy-load the tokenizer"""
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    return _tokenizer

def get_model():
    """Lazy-load the model"""
    global _model
    if _model is None:
        _model = AutoModel.from_pretrained(MODEL_NAME)
    return _model

def mean_pooling(model_output, attention_mask):
    """Mean Pooling - Take attention mask into account for avg pooling"""
    token_embeddings = model_output[0]  # First element of model_output contains token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

def get_embedding(text):
    """Generate embedding for a piece of text"""
    # Get tokenizer and model
    tokenizer = get_tokenizer()
    model = get_model()
    
    # Tokenize text
    encoded_input = tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors='pt')
    
    # Compute token embeddings with no gradient calculation
    with torch.no_grad():
        model_output = model(**encoded_input)
    
    # Perform mean pooling
    sentence_embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
    
    # Convert to numpy array and return
    return sentence_embeddings.numpy()[0]

def serialize_embedding(embedding):
    """Serialize embedding to binary for database storage"""
    return pickle.dumps(embedding)

def deserialize_embedding(binary_data):
    """Deserialize embedding from binary database storage"""
    if binary_data is None:
        return None
    return pickle.loads(binary_data)

def create_or_update_content_embedding(content_object):
    """Create or update BERT embedding for a content object"""
    from .models import ContentEmbedding
    
    # Determine the text to embed based on content type
    if hasattr(content_object, 'title') and hasattr(content_object, 'description'):
        # For video or similar content with title and description
        text = f"{content_object.title} {content_object.description}"
    elif hasattr(content_object, 'title') and hasattr(content_object, 'content'):
        # For blog or similar content with title and content
        text = f"{content_object.title} {content_object.content}"
    elif hasattr(content_object, 'content'):
        # For post or similar content with only content
        text = content_object.content
    else:
        # If no suitable text fields found
        return None
    
    # Generate embedding
    embedding = get_embedding(text)
    serialized_embedding = serialize_embedding(embedding)
    
    # Get content type
    content_type = ContentType.objects.get_for_model(content_object)
    
    # Create or update embedding
    content_embedding, created = ContentEmbedding.objects.update_or_create(
        content_type=content_type,
        object_id=content_object.id,
        defaults={'embedding': serialized_embedding}
    )
    
    return content_embedding

def semantic_search(query, content_types=None, limit=20):
    """
    Perform semantic search using BERT embeddings
    
    Args:
        query (str): The search query text
        content_types (list): Optional list of content_type models to search in
        limit (int): Maximum number of results to return
        
    Returns:
        List of (content_object, similarity_score) tuples
    """
    from .models import ContentEmbedding
    
    # Generate query embedding
    query_embedding = get_embedding(query)
    
    # Prepare filters for ContentEmbedding
    filters = {}
    if content_types:
        content_type_ids = [ContentType.objects.get_for_model(model).id for model in content_types]
        filters['content_type_id__in'] = content_type_ids
    
    # Fetch all content embeddings (could be optimized with pagination for large datasets)
    content_embeddings = ContentEmbedding.objects.filter(**filters)
    
    # Calculate similarity scores
    results = []
    for content_embedding in content_embeddings:
        embedding = deserialize_embedding(content_embedding.embedding)
        if embedding is not None:
            similarity = cosine_similarity([query_embedding], [embedding])[0][0]
            results.append((content_embedding.content_object, similarity))
    
    # Sort by similarity score (descending)
    results.sort(key=lambda x: x[1], reverse=True)
    
    # Return top results
    return results[:limit] 