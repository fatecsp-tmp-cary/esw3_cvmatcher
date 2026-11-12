# Local model validation dependencies

Approved development-only installation for the accepted local inference work.
No global packages, Codex settings, native authentication or paid service changes.
The existing application interpreter is Python 3.12 on the approved Ubuntu host;
Debian/Python 3.13 acceptance remains separate.

Install into `/home/agent/workspace/cvmatcher-dev` after explicit approval:

```sh
/home/agent/workspace/cvmatcher-dev/bin/python -m pip install \
  torch==2.9.1+cpu --index-url https://download.pytorch.org/whl/cpu
/home/agent/workspace/cvmatcher-dev/bin/python -m pip install \
  gliner==0.2.30 sentence-transformers==3.4.1 'transformers>=4.51,<5' \
  mypy==2.4.1 pip-tools==7.6.2 protobuf==7.36.1
```

Resolve and hash the complete dependency graphs before the installation. Run
resource gates before downloading model artifacts; retain only pinned revisions.
Initial evaluation artifacts (not measured release approvals):

- `intfloat/multilingual-e5-small` at
  `614241f622f53c4eeff9890bdc4f31cfecc418b3` (MIT, 384 dimensions).
- `urchade/gliner_multi-v2.1` at
  `443d26d654e0324125a96bebd8e796c14ff2efe6` (Apache-2.0).

Revisions were resolved through the publishers' Hugging Face model API on
2026-11-11. See the [E5 model card](https://huggingface.co/intfloat/multilingual-e5-small)
and [GLiNER model card](https://huggingface.co/urchade/gliner_multi-v2.1).
Models load offline from prepared local caches during service operation. Neither
model download nor live inference is a required ordinary CI dependency. Mandatory
exclusions remain disabled until reviewed evaluation meets the documented quality
gates. Package compatibility, actual CPU inference and five-second request latency
must be measured; this proposal records no passing result.

The user approved the virtualenv installation during this session. The first
real GLiNER smoke identified protobuf as a required tokenizer-conversion
prerequisite missing from upstream dependency metadata. `protobuf==7.36.1` was
added within the approved local-inference installation scope; no alternative
tokenizer or unpinned backbone was substituted. Final smoke results are reported
separately.

The installed sentencepiece 0.2.3 protobuf gencode requires runtime 7.36.1;
the initial 6.33.5 proposal was rejected by its version guard and superseded
before any model inference. The exact compatible version is now pinned above.
