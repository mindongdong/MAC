### Voyage AI Service Utilization Guide

This guide provides comprehensive instructions and examples for utilizing the Voyage AI service, covering API access, Python client usage, text embedding models, flexible dimensions, quantization, rate limits, and tokenization.

#### 1. API Access and Authentication

Voyage AI uses API keys to monitor usage and manage permissions.

*   **Obtaining Your API Key**:
    *   Sign in with your Voyage AI account.
    *   Navigate to the **API keys** section of the Voyage dashboard.
    *   Click the "Create new secret key" button to generate your key.
*   **Security**: Your API key is secret and should be stored securely. **Avoid sharing it or exposing it in browsers or apps**.
*   **Setting the API Key**:
    *   It is **recommended to set the API key as an environment variable**.
    *   For MacOS or Linux, open your terminal and type:
        ```bash
        export VOYAGE_API_KEY="<your secret key>"
        ```
        Replace `<your secret key>` with your actual API key.
    *   **Verification**: You can verify the setup by typing `echo $VOYAGE_API_KEY` in the terminal. It should display your API key.

#### 2. Install Voyage Python Package

You can interact with the API via HTTP requests from any language, but Voyage AI offers an official Python package for Python users.

*   **Installation**:
    *   Install the package using `pip`:
        ```bash
        pip install -U voyageai
        ```
    *   The `-U` or `--upgrade` option is recommended to ensure you install the latest version, providing access to recent features and bug fixes.
*   **Verification**:
    *   After installation, you can test it by running:
        ```bash
        python -c "import voyageai"
        ```
    *   The installation is successful if this command runs without any errors.

#### 3. Python Client Usage

The Python package provides client classes as the interface to invoke Voyage's API.

*   **`voyageai.Client`**:
    *   This class is the interface for **synchronous API calls**.
    *   **Parameters**:
        *   `api_key` (str, optional, defaults to `None`): Your Voyage API key. If `None`, the client searches for the API key in a specific order: `voyageai.api_key_path`, environment variable `VOYAGE_API_KEY_PATH`, `voyageai.api_key` attribute, and finally the environment variable `VOYAGE_API_KEY`.
        *   `max_retries` (int, defaults to 0): **Maximum number of retries** for API requests in case of rate limit errors or temporary server unavailability. By default, the client does not retry. It employs a wait-and-retry strategy and raises an exception upon reaching the limit.
        *   `timeout` (int, optional, defaults to `None`): **Maximum time in seconds** to wait for an API response before aborting. If exceeded, a timeout exception is raised. By default, no timeout constraint is enforced.
    *   **Example**:
        ```python
        import voyageai
        # This will automatically use the environment variable VOYAGE_API_KEY.
        vo = voyageai.Client()
        # Alternatively, you can explicitly pass the API key:
        # vo = voyageai.Client(api_key="<your secret key>")
        
        result = vo.embed(["hello world"], model="voyage-3.5")
        # The result object contains embeddings and total_tokens
        print(result.embeddings)
        print(result.total_tokens)
        ```
       

*   **`voyageai.AsyncClient`**:
    *   Designed for **asynchronous API calls**, mirroring the `Client` class in method offerings and specifications but tailored for non-blocking operations.
    *   **Example**:
        ```python
        import voyageai
        # This will automatically use the environment variable VOYAGE_API_KEY.
        vo = voyageai.AsyncClient()
        # Alternatively, you can explicitly pass the API key:
        # vo = voyageai.AsyncClient(api_key="<your secret key>")
        
        # Note: 'await' can only be used inside an async function
        # result = await vo.embed(["hello world"], model="voyage-3.5")
        ```
       

#### 4. Text Embedding Models

Voyage AI offers various text embedding models optimized for different purposes.

*   **Key Models and Their Characteristics**:
    *   **`voyage-3-large`, `voyage-3.5`, `voyage-3.5-lite`**: Optimized for general-purpose and multilingual retrieval quality. Most have a **32,000 token context length** and a default embedding dimension of **1024**.
    *   **`voyage-code-3`**: Optimized for **code retrieval**.
    *   **`voyage-finance-2`**: Optimized for **financial retrieval and RAG** (Retrieval Augmented Generation).
    *   **`voyage-law-2`**: Optimized for **legal retrieval and RAG**.
    *   **Context Length**: Most models have a 32,000 token context length, though `voyage-law-2` and older models might have different lengths (e.g., 16,000 or 4,000).
    *   **Embedding Dimension**: Default is 1024. Some models (`voyage-3-large`, `voyage-3.5`, `voyage-3.5-lite`, `voyage-code-3`) support multiple output dimensions: 256, 512, 1024 (default), and 2048.

*   **`voyageai.Client.embed()` Function**:
    *   This function is used to vectorize your inputs.
    *   **Signature**:
        ```python
        voyageai.Client.embed(texts : List[str], model : str, input_type : Optional[str] = None, truncation : Optional[bool] = None, output_dimension: Optional[int] = None, output_dtype: Optional[str] = "float")
        ```
       
    *   **Parameters**:
        *   `texts` (str or List[str]): The text(s) to be embedded. This can be a single string or a list of up to 1,000 strings.
            *   **Constraints**: The total number of tokens in the list must not exceed certain limits based on the model (e.g., 1M for `voyage-3.5-lite`, 320K for `voyage-3.5`, 120K for `voyage-3-large`).
        *   `model` (str): The name of the model to use (e.g., `voyage-3.5`).
        *   `input_type` (str, optional, defaults to `None`): Specifies the type of input text. Options are `None`, `query`, or `document`.
            *   For retrieval/search tasks, specifying `query` or `document` is recommended. Voyage AI automatically **prepends a prompt** to your input text before vectorizing to optimize embeddings for search.
            *   **Prompts**:
                *   For `query`: " *Represent the query for retrieving supporting documents:* ".
                *   For `document`: " *Represent the document for retrieval:* ".
            *   Embeddings generated with and without `input_type` are compatible.
        *   `truncation` (bool, optional, defaults to `True`): Determines whether to truncate input texts that exceed the model's context length.
            *   If `True`, over-length texts are truncated.
            *   If `False`, an error is raised if any text exceeds the context length.
        *   `output_dimension` (int, optional, defaults to `None`): The desired number of dimensions for the output embeddings.
            *   Supported by `voyage-3-large`, `voyage-3.5`, `voyage-3.5-lite`, and `voyage-code-3` for values: 256, 512, 1024 (default), and 2048.
        *   `output_dtype` (str, optional, defaults to `float`): The data type for the returned embeddings.
            *   Options: `float`, `int8`, `uint8`, `binary`, `ubinary`.
            *   `float` is supported by all models and provides the highest precision.
            *   `int8`, `uint8`, `binary`, and `ubinary` are supported by `voyage-3-large`, `voyage-3.5`, `voyage-3.5-lite`, and `voyage-code-3`.
    *   **Returns**: An `EmbeddingsObject` containing:
        *   `embeddings` (List[List[float]] or List[List[int]]): A list of embedding vectors.
        *   `total_tokens` (int): The total number of tokens in the input texts.
    *   **Example**:
        ```python
        import voyageai
        vo = voyageai.Client()
        texts = [
            "The Mediterranean diet emphasizes fish, olive oil, and vegetables, believed to reduce chronic diseases.",
            "Photosynthesis in plants converts light energy into glucose and produces essential oxygen."
        ]
        
        result = vo.embed(texts, model="voyage-3.5", input_type="document")
        print(result.embeddings)
        print(result.total_tokens)
        ```
       

#### 5. Flexible Dimensions and Quantization

Flexible dimensions and quantization are used to **reduce storage and search costs** for large corpora by lowering embedding dimensionality and precision.

*   **Matryoshka Embeddings**:
    *   Matryoshka learning creates embeddings with a **nested family of embeddings with various lengths within a single vector**.
    *   Specifically, for `k` in {256, 512, and 1024}, the first `k` entries of a 2048-dimensional embedding also form a valid `k`-dimensional embedding with a slight loss of retrieval quality.
    *   This allows users to vectorize documents into a long 2048-dimensional vector once and then use shorter versions by taking the first `k` entries **without re-invoking the embedding model**.
    *   Newer models like `voyage-3-large` directly support multiple output dimensions via the `output_dimension` parameter.
    *   **Truncating Matryoshka Embeddings**: You can truncate by keeping the leading subset of dimensions.
        ```python
        import voyageai
        import numpy as np
        
        def embd_normalize(v: np.ndarray) -> np.ndarray:
            """Normalize the rows of a 2D NumPy array to unit vectors."""
            row_norms = np.linalg.norm(v, axis=1, keepdims=True)
            if np.any(row_norms == 0):
                raise ValueError("Cannot normalize rows with a norm of zero.")
            return v / row_norms
        
        vo = voyageai.Client()
        # Generate voyage-3-large vectors, default 1024-dimensional floats
        embd = vo.embed(['Sample text 1', 'Sample text 2'], model='voyage-3-large').embeddings
        
        # Set shorter dimension
        short_dim = 256
        
        # Resize and normalize vectors to shorter dimension
        resized_embd = embd_normalize(np.array(embd)[:, :short_dim]).tolist()
        print(f"Original dimension: {len(embd)}")
        print(f"Resized dimension: {len(resized_embd)}")
        ```
       

*   **Quantization**:
    *   Quantized embeddings have **lower precision** (e.g., 8 bits or 1 bit per dimension), which **reduces storage costs** by 4x or 32x compared to 32-bit floats.
    *   Newer Voyage embedding models (`voyage-3-large`, `voyage-3.5`, `voyage-3.5-lite`, `voyage-code-3`) support lower-precision embeddings by specifying the `output_dtype` parameter.
    *   **Supported Data Types for `output_dtype`**:
        *   `float`: Default, 32-bit (4-byte) single-precision floating-point numbers, highest precision.
        *   `int8`: 8-bit (1-byte) signed integers (-128 to 127).
        *   `uint8`: 8-bit (1-byte) unsigned integers (0 to 255).
        *   `binary`: Bit-packed single-bit embedding values represented as `int8`. The length of the returned list is **1/8 of the actual embedding dimension**. Uses the **offset binary method** for negative numbers.
        *   `ubinary`: Bit-packed single-bit embedding values represented as `uint8`. The length is 1/8 of the actual dimension.
    *   **Offset Binary Method**: A method for representing negative numbers in binary form. An offset (typically 128 for 8-bit signed integers) is added before converting to binary and subtracted when converting back to a signed integer.
        *   **Example (Signed integer to binary)**: To represent -32 as an 8-bit binary number:
            1.  Add offset (128) to -32: 96.
            2.  Convert 96 to binary: `01100000`.
        *   **Example (Binary to signed integer)**: To determine the signed integer from `01010101`:
            1.  Convert to integer: 85.
            2.  Subtract offset (128) from 85: -43.
    *   **Python Code Examples for Binary Embeddings**:
        ```python
        import numpy as np
        import voyageai
        
        vo = voyageai.Client()
        
        # Generate float embeddings
        embd_float = vo.embed('Sample text 1', model='voyage-3-large', output_dimension=2048).embeddings
        
        # Compute 512-dimensional bit-packed binary and ubinary embeddings from 2048-dimensional float embeddings
        # Note: These calculations are for demonstration based on the provided source's method,
        # usually you'd directly request the output_dtype from the API if supported.
        embd_binary_calc = (np.packbits(np.array(embd_float) > 0, axis=0) - 128).astype(np.int8).tolist() # Quantize, binary offset
        embd_binary_512_calc = embd_binary_calc[0:64] # Truncate (512 / 8 = 64)
        
        embd_ubinary_calc = (np.packbits(np.array(embd_float) > 0, axis=0)).astype(np.uint8).tolist() # Quantize, unsigned binary
        embd_ubinary_512_calc = embd_ubinary_calc[0:64] # Truncate (512 / 8 = 64)
        
        # Directly generate binary embeddings from the API
        embd_binary = vo.embed('Sample text 1', model='voyage-3-large', output_dtype='binary', output_dimension=2048).embeddings
        embd_ubinary = vo.embed('Sample text 1', model='voyage-3-large', output_dtype='ubinary', output_dimension=2048).embeddings
        
        # Unpack bits for verification
        embd_binary_bits = [format(x, f'08b') for x in np.array(embd_binary) + 128] # List of (bits) strings
        embd_binary_unpacked = [bit == '1' for bit in ''.join(embd_binary_bits)] # List of booleans
        
        embd_ubinary_bits = [format(x, f'08b') for x in np.array(embd_ubinary)] # List of (bits) strings
        embd_ubinary_unpacked = [bit == '1' for bit in ''.join(embd_ubinary_bits)] # List of booleans
        
        print(f"Direct binary embedding (first 5 bytes): {embd_binary[:5]}")
        print(f"Direct ubinary embedding (first 5 bytes): {embd_ubinary[:5]}")
        print(f"Unpacked binary bits (first 8): {embd_binary_unpacked[:8]}")
        ```
       

#### 6. Rate Limits (Usage Limits)

Voyage AI imposes **rate limits** to ensure fair and efficient API usage, preventing excessive traffic that could impact overall service performance.

*   **Types of Limits**:
    *   **RPM (Requests Per Minute)**: Number of requests allowed per minute.
    *   **TPM (Tokens Per Minute)**: Number of tokens that can be processed per minute.
*   **Basic Rate Limits (Example for `voyage-3.5`)**: 2000 RPM and 8M TPM.
*   **Reasons for Rate Limits**:
    1.  **Equitable Access**: Ensures all users can utilize the API without performance issues caused by excessive requests from one entity.
    2.  **Workload Management**: Helps manage server resources to maintain consistent and reliable performance.
    3.  **Safeguard Against Abuse**: Prevents malicious actors from overloading or disrupting services.
*   **Usage Tiers**:
    *   Rate limits increase automatically as your usage and spending grow.
    *   **Qualification is based on billed usage**, excluding free tokens.
    *   Once qualified, you are **never downgraded** to a lower tier.
    *   **Tiers**:
        *   **Tier 1**: Payment method added (basic limits, e.g., 2000 RPM, 8M TPM for `voyage-3.5`).
        *   **Tier 2**: ≥ $100 paid (2x Tier 1 limits, e.g., 4000 RPM, 16M TPM for `voyage-3.5`).
        *   **Tier 3**: ≥ $1000 paid (3x Tier 1 limits, e.g., 6000 RPM, 24M TPM for `voyage-3.5`).
    *   You can view your organization's rate limits in the Voyage dashboard's **Rate Limits** section.
*   **Project Rate Limits**:
    *   Organization admins can set project-level rate limits.
    *   These must be **less than or equal to the organization's corresponding rate limit**.
    *   **Impact of Organization Limits**: If the sum of all project rate limits exceeds the organization limit, the organization limit might be reached first, potentially leading to individual projects being rate-limited at a lower rate than their set limits.
*   **Exceeding Rate Limits**: If you exceed a rate limit, you will receive an **error message with the code 429**.
*   **How to Avoid Hitting Rate Limits**:
    *   **Use Larger Batches**: Send more documents per request to reduce your overall RPM.
        *   **Example**: Vectorizing 512 documents with a batch size of 1 requires 512 requests (high RPM), but a batch size of 128 requires only 4 requests (lower RPM).
        ```python
        import voyageai
        # Boilerplate code for demonstration
        vo = voyageai.Client()
        documents = [
            "The Mediterranean diet emphasizes fish, olive oil, and vegetables, believed to reduce chronic diseases.",
            "Photosynthesis in plants converts light energy into glucose and produces essential oxygen.",
            "20th-century innovations, from radios to smartphones, centered on electronic advancements.",
            "Rivers provide water, irrigation, and habitat for aquatic species, vital for ecosystems.",
            "Apple’s conference call to discuss fourth fiscal quarter results and business updates is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.",
            "Shakespeare's works, like 'Hamlet' and 'A Midsummer Night's Dream,' endure in literature."
        ]
        
        # Embed more than 128 documents in a for loop (example with small document list)
        batch_size = 2 # Using smaller batch_size for demonstration with limited documents
        embeddings = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            print(f"Embedding documents {i} to {i + len(batch) - 1}")
            # print("Total tokens in batch:", vo.count_tokens(batch, model="voyage-3.5")) # Requires tokenizers package
            batch_embeddings = vo.embed(
                batch,
                model="voyage-3.5",
                input_type="document"
            ).embeddings
            embeddings += batch_embeddings
            print(f"Batch {i//batch_size + 1} embeddings preview: {batch_embeddings[:5]}...")
        print("Total embeddings generated:", len(embeddings))
        ```
       
        *   Consider API maximum batch size and total token limits per request.
    *   **Set a Wait Period**: Pace your requests by inserting a delay between them.
        ```python
        import voyageai
        import time
        
        vo = voyageai.Client()
        documents = [ # ... (same documents list as above) ... ]
        
        batch_size = 2 # Using smaller batch_size for demonstration with limited documents
        embeddings = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            embeddings += vo.embed(
                batch,
                model="voyage-3.5",
                input_type="document"
            ).embeddings
            time.sleep(0.1) # Add a small amount of sleep in between each iteration
            print(f"Processed batch {i//batch_size + 1}, waiting 0.1s...")
        print("Finished processing all documents with wait periods.")
        ```
       
    *   **Exponential Backoff**: When a 429 error occurs, wait for an exponentially increasing time before retrying until successful or a maximum retry limit is reached.
        *   This can be implemented using libraries like `tenacity`.
        ```python
        import voyageai
        from tenacity import (
            retry,
            stop_after_attempt,
            wait_random_exponential,
        )
        
        vo = voyageai.Client()
        documents = [ # ... (same documents list as above) ... ]
        
        @retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_attempt(6))
        def embed_with_backoff(**kwargs):
            return vo.embed(**kwargs)
        
        try:
            result = embed_with_backoff(texts=documents, model="voyage-3.5", input_type="document")
            print("Embeddings generated successfully with backoff.")
            print(result.embeddings[:5])
        except Exception as e:
            print(f"Failed to generate embeddings after multiple retries: {e}")
        ```
       
    *   **Request Rate Limit Increase**: If the above methods are insufficient, you can request a higher rate limit from Voyage AI.

#### 7. Error Codes and Solutions

The API may return various error codes indicating issues.

*   **400 Invalid Request**:
    *   **Cause**: Invalid request body (not valid JSON), invalid parameter, wrong parameter type, batch size too large, total tokens in batch exceeding limit, or tokens in an example exceeding context length.
    *   **Solution**: Check the request body and correct errors, which will be indicated in the error message.
*   **401 Unauthorized**:
    *   **Cause**: Invalid authentication.
    *   **Solution**: Ensure the API key is correctly specified in the HTTP request header. Create or view your API key in the dashboard.
*   **403 Forbidden**:
    *   **Cause**: The IP address sending the request might be forbidden.
    *   **Solution**: Try using a different IP address.
*   **429 Rate Limit Exceeded**:
    *   **Cause**: Request frequency is too high.
    *   **Solution**: Pace your requests. Refer to the rate limit guide for strategies (larger batches, wait periods, exponential backoff).
*   **500 Server Error**:
    *   **Cause**: Unexpected issue on Voyage AI servers.
    *   **Solution**: Retry your request after a brief wait. If it persists, contact support.
*   **502, 503, 504 Service Unavailable**:
    *   **Cause**: Servers are experiencing high traffic.
    *   **Solution**: Retry your requests after a brief wait.

#### 8. Tokenization

**Tokenization** is the first step of the embedding/reranking process, where input text is dissected into a list of tokens. This is **automatically performed on Voyage AI servers** when you call the API.

*   **Voyage's Tokenizers**: Voyage AI open-sources its tokenizers on Hugging Face. You can access them using `transformers.AutoTokenizer.from_pretrained('voyageai/voyage-3.5')`.
    *   **Note**: Newer Voyage models use different tokenizers than earlier models, which used the same tokenizer as Llama 2. Always specify the model when using tokenizer functions.
*   **`voyageai.Client.tokenize()` Function**:
    *   Allows you to preview tokenized results.
    *   **Signature**: `voyageai.Client.tokenize(texts : List[str], model: str)`.
    *   **Parameters**: `texts` (List[str]) - list of texts to be tokenized; `model` (str) - name of the model (e.g., `voyage-3.5`).
    *   **Returns**: A list of `tokenizers.Encoding` objects.
    *   **Example**:
        ```python
        import voyageai
        vo = voyageai.Client()
        texts = [
            "The Mediterranean diet emphasizes fish, olive oil, and vegetables, believed to reduce chronic diseases.",
            "Photosynthesis in plants converts light energy into glucose and produces essential oxygen."
        ]
        
        tokenized = vo.tokenize(texts, model="voyage-3.5")
        for i in range(len(texts)):
            print(f"Text: '{texts[i]}'")
            print(f"Tokens: {tokenized[i].tokens}")
        ```
       

*   **`voyageai.Client.count_tokens()` Function**:
    *   Used to determine the exact number of tokens in your input texts.
    *   **Signature**: `voyageai.Client.count_tokens(texts : List[str], model: str)`.
    *   **Parameters**: `texts` (List[str]) - list of texts; `model` (str) - name of the model.
    *   **Returns**: The total number of tokens as an integer.
    *   **Example**:
        ```python
        import voyageai
        vo = voyageai.Client()
        texts = [
            "The Mediterranean diet emphasizes fish, olive oil, and vegetables, believed to reduce chronic diseases.",
            "Photosynthesis in plants converts light energy into glucose and produces essential oxygen."
        ]
        
        total_tokens = vo.count_tokens(texts, model="voyage-3.5")
        print(f"Total tokens for provided texts: {total_tokens}")
        ```
       

*   **`voyageai.Client.count_usage()` Function**:
    *   Calculates text tokens, image pixels, and total tokens for **multimodal models** (currently only `voyage-multimodal-3` is supported). Every 560 pixels counts as a token.
    *   **Signature**: `voyageai.Client.count_usage(inputs : List[dict] or List[List[Union[str, PIL.Image.Image]]] , model: str)`.
    *   **Returns**: A dictionary with `text_tokens`, `image_pixels`, and `total_tokens`.
    *   **Example**:
        ```python
        import voyageai
        import PIL # You would need to have PIL/Pillow installed and an image file
        
        # Assuming 'banana.jpg' exists in your working directory
        # This example requires setting up an actual image file.
        # inputs = [ ["This is a banana.", PIL.Image.open('banana.jpg')] ]
        # usage = vo.count_usage(inputs, model="voyage-multimodal-3")
        # print(usage) # Expected output: {'text_tokens': 5, 'image_pixels': 2000000, 'total_tokens': 3576}
        
        # Since I cannot create an image file, I'll provide a conceptual usage example:
        print("count_usage is for multimodal models like 'voyage-multimodal-3' and requires image inputs.")
        print("Example from source shows calculation where every 560 pixels counts as a token.")
        ```
       

*   **Tokens, Words, and Characters**:
    *   Modern NLP models convert text into tokens.
    *   One word roughly corresponds to **1.2 - 1.5 tokens on average**.
    *   Tokens produced by Voyage's tokenizer have an **average of 5 characters**.
    *   To get the exact token count, use `count_tokens()`.
*   **`tiktoken` vs. Voyage Tokenizers**:
    *   Voyage models use different tokenizers than OpenAI's `tiktoken`.
    *   Voyage's tokenizers generate **1.1 - 1.2 times more tokens on average** than `tiktoken` for the same text.
    *   Use `count_tokens()` for exact counts with Voyage models.