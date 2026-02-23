#!/usr/bin/env python3
"""Test del LLM Factory de AIFoundry."""

import asyncio
from aifoundry.app.core.models import get_llm, reset_llm

# Test 1: Sync
print("🔄 Test Sync...")
llm = get_llm()
response = llm.invoke("Di 'Hola, ¿qué tal?'")
print(f"✅ Sync: {response.content[:50]}...")

# Test 2: Async
print("\n🔄 Test Async...")
reset_llm()

async def test_async():
    llm = get_llm()
    return await llm.ainvoke("Di 'Async funciona'")

response = asyncio.run(test_async())
print(f"✅ Async: {response.content[:50]}...")

# Test 3: Singleton
print("\n🔄 Test Singleton...")
reset_llm()
llm1 = get_llm()
llm2 = get_llm()
assert llm1 is llm2, "Singleton failed!"
print(f"✅ Singleton: llm1 is llm2 = {llm1 is llm2}")

print("\n" + "=" * 40)
print("✅ Sync Completion:   OK")
print("✅ Async Completion:  OK")
print("✅ Singleton Pattern: OK")
