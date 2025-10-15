```
# 콘다 가상환경 생성
conda create -n llama_env python=3.12
# 콘다 가상환경 활성화
conda activate llama_env
#콘다 가상환경 비활성화
conda deativate
```


### LlamaModel 다운로드

- 다운로드 전에 accsess_token 입력 필요.
huggingface-cli login
> <.env token 값 입력>

python llama_download.py

