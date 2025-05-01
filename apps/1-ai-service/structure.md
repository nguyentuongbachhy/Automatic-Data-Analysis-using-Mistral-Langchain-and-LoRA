# Cấu trúc thư mục

├── .env
├── Architechture.md
├── README.md
├── app
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── middleware
│   │   │   ├── auth.py
│   │   │   ├── error_handler.py
│   │   │   └── rate_limiter.py
│   │   └── routers
│   │       ├── __init__.py
│   │       ├── analyze_router.py
│   │       ├── chat_router.py
│   │       └── health_router.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── config.py
│   │   ├── errors.py
│   │   ├── logging.py
│   │   ├── monitoring.py
│   │   └── tasks.py
│   ├── main.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── chat.py
│   │   └── common.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── analyze_service.py
│   │   ├── base_service.py
│   │   ├── chat
│   │   │   ├── __init__.py
│   │   │   └── chat_service.py
│   │   ├── intent_service.py
│   │   ├── model_service.py
│   │   ├── streaming
│   │   │   ├── __init__.py
│   │   │   └── streaming_manager.py
│   │   └── validation_service.py
│   ├── structure.md
│   └── utils
│       ├── __init__.py
│       ├── file_utils.py
│       ├── json_encoder.py
│       └── profiler.py
├── configs
│   ├── logging_config.json
│   ├── model_config.json
│   └── plugins_config.json
├── data
│   ├── label_mapping.json
│   ├── lora_testing.jsonl
│   ├── lora_training.jsonl
│   └── lora_training_v2.jsonl
├── integration-diagram.mermaid
├── ml
│   ├── __init__.py
│   ├── analysis
│   │   ├── __init__.py
│   │   ├── analyzer.py
│   │   └── time_series.py
│   ├── data
│   │   ├── __init__.py
│   │   ├── data_processor.py
│   │   └── data_validator.py
│   ├── functions.md
│   ├── get_structure.py
│   ├── model
│   │   ├── __init__.py
│   │   ├── mistral_inference.py
│   │   └── model_manager.py
│   ├── structure.md
│   ├── utils
│   │   ├── __init__.py
│   │   ├── datetime_utils.py
│   │   └── memory_utils.py
│   └── visualization
│       ├── charts.py
│       ├── insights.py
│       └── recommender.py
├── mlruns
│   ├── .trash
│   └── 0
│       ├── 9ef14681caa2433588de58e27b4167c2
│       │   ├── artifacts
│       │   ├── meta.yaml
│       │   ├── metrics
│       │   ├── params
│       │   │   ├── _attn_implementation_autoset
│       │   │   ├── _name_or_path
│       │   │   ├── accelerator_config
│       │   │   ├── adafactor
│       │   │   ├── adam_beta1
│       │   │   ├── adam_beta2
│       │   │   ├── adam_epsilon
│       │   │   ├── add_cross_attention
│       │   │   ├── architectures
│       │   │   ├── attention_dropout
│       │   │   ├── auto_find_batch_size
│       │   │   ├── average_tokens_across_devices
│       │   │   ├── bad_words_ids
│       │   │   ├── batch_eval_metrics
│       │   │   ├── begin_suppress_tokens
│       │   │   ├── bf16
│       │   │   ├── bf16_full_eval
│       │   │   ├── bos_token_id
│       │   │   ├── chunk_size_feed_forward
│       │   │   ├── cross_attention_hidden_size
│       │   │   ├── data_seed
│       │   │   ├── dataloader_drop_last
│       │   │   ├── dataloader_num_workers
│       │   │   ├── dataloader_persistent_workers
│       │   │   ├── dataloader_pin_memory
│       │   │   ├── dataloader_prefetch_factor
│       │   │   ├── ddp_backend
│       │   │   ├── ddp_broadcast_buffers
│       │   │   ├── ddp_bucket_cap_mb
│       │   │   ├── ddp_find_unused_parameters
│       │   │   ├── ddp_timeout
│       │   │   ├── debug
│       │   │   ├── decoder_start_token_id
│       │   │   ├── deepspeed
│       │   │   ├── disable_tqdm
│       │   │   ├── dispatch_batches
│       │   │   ├── diversity_penalty
│       │   │   ├── do_eval
│       │   │   ├── do_predict
│       │   │   ├── do_sample
│       │   │   ├── do_train
│       │   │   ├── early_stopping
│       │   │   ├── encoder_no_repeat_ngram_size
│       │   │   ├── eos_token_id
│       │   │   ├── eval_accumulation_steps
│       │   │   ├── eval_delay
│       │   │   ├── eval_do_concat_batches
│       │   │   ├── eval_on_start
│       │   │   ├── eval_steps
│       │   │   ├── eval_strategy
│       │   │   ├── eval_use_gather_object
│       │   │   ├── evaluation_strategy
│       │   │   ├── exponential_decay_length_penalty
│       │   │   ├── finetuning_task
│       │   │   ├── forced_bos_token_id
│       │   │   ├── forced_eos_token_id
│       │   │   ├── fp16
│       │   │   ├── fp16_backend
│       │   │   ├── fp16_full_eval
│       │   │   ├── fp16_opt_level
│       │   │   ├── fsdp
│       │   │   ├── fsdp_config
│       │   │   ├── fsdp_min_num_params
│       │   │   ├── fsdp_transformer_layer_cls_to_wrap
│       │   │   ├── full_determinism
│       │   │   ├── gradient_accumulation_steps
│       │   │   ├── gradient_checkpointing
│       │   │   ├── gradient_checkpointing_kwargs
│       │   │   ├── greater_is_better
│       │   │   ├── group_by_length
│       │   │   ├── half_precision_backend
│       │   │   ├── head_dim
│       │   │   ├── hidden_act
│       │   │   ├── hidden_size
│       │   │   ├── hub_always_push
│       │   │   ├── hub_model_id
│       │   │   ├── hub_private_repo
│       │   │   ├── hub_strategy
│       │   │   ├── hub_token
│       │   │   ├── id2label
│       │   │   ├── ignore_data_skip
│       │   │   ├── include_for_metrics
│       │   │   ├── include_inputs_for_metrics
│       │   │   ├── include_num_input_tokens_seen
│       │   │   ├── include_tokens_per_second
│       │   │   ├── initializer_range
│       │   │   ├── intermediate_size
│       │   │   ├── is_decoder
│       │   │   ├── is_encoder_decoder
│       │   │   ├── jit_mode_eval
│       │   │   ├── label2id
│       │   │   ├── label_names
│       │   │   ├── label_smoothing_factor
│       │   │   ├── learning_rate
│       │   │   ├── length_column_name
│       │   │   ├── length_penalty
│       │   │   ├── load_best_model_at_end
│       │   │   ├── local_rank
│       │   │   ├── log_level
│       │   │   ├── log_level_replica
│       │   │   ├── log_on_each_node
│       │   │   ├── logging_dir
│       │   │   ├── logging_first_step
│       │   │   ├── logging_nan_inf_filter
│       │   │   ├── logging_steps
│       │   │   ├── logging_strategy
│       │   │   ├── lr_scheduler_kwargs
│       │   │   ├── lr_scheduler_type
│       │   │   ├── max_grad_norm
│       │   │   ├── max_length
│       │   │   ├── max_position_embeddings
│       │   │   ├── max_steps
│       │   │   ├── metric_for_best_model
│       │   │   ├── min_length
│       │   │   ├── model_type
│       │   │   ├── mp_parameters
│       │   │   ├── neftune_noise_alpha
│       │   │   ├── no_cuda
│       │   │   ├── no_repeat_ngram_size
│       │   │   ├── num_attention_heads
│       │   │   ├── num_beam_groups
│       │   │   ├── num_beams
│       │   │   ├── num_hidden_layers
│       │   │   ├── num_key_value_heads
│       │   │   ├── num_return_sequences
│       │   │   ├── num_train_epochs
│       │   │   ├── optim
│       │   │   ├── optim_args
│       │   │   ├── optim_target_modules
│       │   │   ├── output_attentions
│       │   │   ├── output_dir
│       │   │   ├── output_hidden_states
│       │   │   ├── output_scores
│       │   │   ├── overwrite_output_dir
│       │   │   ├── pad_token_id
│       │   │   ├── past_index
│       │   │   ├── per_device_eval_batch_size
│       │   │   ├── per_device_train_batch_size
│       │   │   ├── per_gpu_eval_batch_size
│       │   │   ├── per_gpu_train_batch_size
│       │   │   ├── prediction_loss_only
│       │   │   ├── prefix
│       │   │   ├── problem_type
│       │   │   ├── pruned_heads
│       │   │   ├── push_to_hub
│       │   │   ├── push_to_hub_model_id
│       │   │   ├── push_to_hub_organization
│       │   │   ├── push_to_hub_token
│       │   │   ├── quantization_config
│       │   │   ├── ray_scope
│       │   │   ├── remove_invalid_values
│       │   │   ├── remove_unused_columns
│       │   │   ├── repetition_penalty
│       │   │   ├── report_to
│       │   │   ├── restore_callback_states_from_checkpoint
│       │   │   ├── resume_from_checkpoint
│       │   │   ├── return_dict
│       │   │   ├── return_dict_in_generate
│       │   │   ├── rms_norm_eps
│       │   │   ├── rope_theta
│       │   │   ├── run_name
│       │   │   ├── save_on_each_node
│       │   │   ├── save_only_model
│       │   │   ├── save_safetensors
│       │   │   ├── save_steps
│       │   │   ├── save_strategy
│       │   │   ├── save_total_limit
│       │   │   ├── seed
│       │   │   ├── sep_token_id
│       │   │   ├── skip_memory_metrics
│       │   │   ├── sliding_window
│       │   │   ├── split_batches
│       │   │   ├── suppress_tokens
│       │   │   ├── task_specific_params
│       │   │   ├── temperature
│       │   │   ├── tf32
│       │   │   ├── tf_legacy_loss
│       │   │   ├── tie_encoder_decoder
│       │   │   ├── tie_word_embeddings
│       │   │   ├── tokenizer_class
│       │   │   ├── top_k
│       │   │   ├── top_p
│       │   │   ├── torch_compile
│       │   │   ├── torch_compile_backend
│       │   │   ├── torch_compile_mode
│       │   │   ├── torch_dtype
│       │   │   ├── torch_empty_cache_steps
│       │   │   ├── torchdynamo
│       │   │   ├── torchscript
│       │   │   ├── tp_size
│       │   │   ├── tpu_metrics_debug
│       │   │   ├── tpu_num_cores
│       │   │   ├── transformers_version
│       │   │   ├── typical_p
│       │   │   ├── use_bfloat16
│       │   │   ├── use_cache
│       │   │   ├── use_cpu
│       │   │   ├── use_ipex
│       │   │   ├── use_legacy_prediction_loop
│       │   │   ├── use_liger_kernel
│       │   │   ├── use_mps_device
│       │   │   ├── vocab_size
│       │   │   ├── warmup_ratio
│       │   │   ├── warmup_steps
│       │   │   └── weight_decay
│       │   └── tags
│       │       ├── mlflow.runName
│       │       ├── mlflow.source.git.commit
│       │       ├── mlflow.source.name
│       │       ├── mlflow.source.type
│       │       └── mlflow.user
│       └── meta.yaml
├── models
│   ├── base
│   │   └── Mistral-7B-v0.1
│   │       ├── special_tokens_map.json
│   │       ├── tokenizer.json
│   │       └── tokenizer_config.json
│   ├── finetuned
│   └── lora-intent-detection
│       ├── adapter_config.json
│       ├── adapter_model.safetensors
│       ├── special_tokens_map.json
│       ├── tokenizer.json
│       ├── tokenizer.model
│       ├── tokenizer_config.json
│       └── training_args.bin
├── pytest.ini
├── requirements.txt
├── scripts
│   ├── __init__.py
│   ├── convert_spider_to_intents.py
│   ├── download_dataset.py
│   ├── prepare_datasets.py
│   ├── train_lora.py
│   └── train_lora_v2.py
└── tests
    ├── __init__.py
    ├── conftest.py
    ├── test_api
    │   ├── __init__.py
    │   ├── test_analyze_router.py
    │   ├── test_chat_router.py
    │   └── test_health_router.py
    ├── test_ml
    │   ├── __init__.py
    │   ├── test_data
    │   │   └── Chocolate Sales.csv
    │   ├── test_data_cleaning.py
    │   └── test_inference.py
    ├── test_services
    │   ├── __init__.py
    │   ├── test_analyze_service.py
    │   ├── test_chat_service.py
    │   ├── test_chat_service_integration.py
    │   ├── test_model_service.py
    │   ├── test_model_service_intent.py
    │   └── test_validation_service.py
    └── test_utils
        ├── __init__.py
        └── mock_data.py