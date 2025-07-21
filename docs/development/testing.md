## Frosty AI Testing

### Test Types
1. **Unit Tests** - Validation logic
   ```python
   def test_missing_key_detection():
       chain = ChainSpec(...)  # Chain missing API key
       result = validate(chain)
       assert "Missing API key" in result.errors
   ```
   
2. **Interactive Tests** - User flows
   ```python
   @pytest.mark.interactive
   async def test_weather_flow():
       frosty = FrostyAIService(test_mode=True)
       chain = await frosty.generate_chain_interactive(...)
       assert chain.is_executable
   ```

3. **Golden Tests** - Training examples
   ```python
   def test_training_examples():
       for example in load_training_data():
           assert_valid(example.chain)
   ``` 