# MDXtract
MDXtract is a set of python tools for extracting instrument and sample data from files used by the [MXDRV](https://www16.atwiki.jp/mxdrv/pages/23.html) and PMD sound drivers. Both are binary [MML](https://en.wikipedia.org/wiki/Music_Macro_Language) representations and were extremely popular on Japanese PCs of the 1990s including the NEC [PC-88](https://en.wikipedia.org/wiki/PC-8800_series)/[9801](https://en.wikipedia.org/wiki/PC-9800_series) and Sharp [X68000](https://en.wikipedia.org/wiki/X68000) computer lines. 

The higher end models were equipped with the amazing [YM2151](https://en.wikipedia.org/wiki/Yamaha_YM2151) (OPM) and [YM2608](https://en.wikipedia.org/wiki/Yamaha_YM2608) (OPNA) FM tone generators, and the main purpose behind the MDXtract tools is to extract instrument definitions for these chips and convert them to [DX7](https://en.wikipedia.org/wiki/Yamaha_DX7) compatible [sysex](http://electronicmusic.wikia.com/wiki/System_exclusive) data. The data can be imported into many [popular](https://asb2m10.github.io/dexed/) [software](https://www.arturia.com/dx7-v/overview) [FM](https://www.native-instruments.com/en/products/komplete/synths/fm8/) synthesizers, as well as the original hardware.

Included are also tools to extract and convert ADPCM sample data from the supplementary sample archive formats used by these sound drivers; PDX, PPC, PPS, PVI, P86, et cetera.


## operation

**mdx2syx.py**
```
mdx2syx.py [-h, --help] [-v, --verbose] [infiles ...]
```
 - Instrument data will be converted and written as `<filename>.syx`.
 - In verbose mode some intriguing data will be printed to stdout.

**pmd2syx.py**
```
pmd2syx.py [-h, --help] [-v, --verbose] [infiles ...]
```
 - Common PMD extensions are .M and .M2.
 - Instrument data will be converted and written as `<filename>.syx`.
 - In verbose mode some very intriguing data will be printed to stdout.

**pdx2wav.py**
```
pdx2wav.py [-h] [-v] [--rate R] [--gain G] [--dcnorm] [infiles ...]
```
 - ADPCM data will be converted and written as `<filename>_<n>.wav`.
 - Default sample rate is 15625 Hz, the most common setting on a X68000.
 - In verbose mode some not-so-intriguing data will be printed to stdout.

**pmd2wav.py**
```
pmd2wav.py [-h] [-v] --type [type] [--rate R] [--gain G] [--dcnorm] [infiles ...]
```
 - Common PMD sample archive extensions include .PPC, .P86 and .PPS.
 - It is usually not needed to specify `type`. When omitted the tool will auto detect the format by looking at the file header, and if nothing can be deduced from that it falls back to the file extension. 
 - AD/PCM data will be converted and written as `<filename>_<n>.wav`.
 - Default sample rate is 15625 Hz, not a common setting on PC-9801!
 - In verbose mode something will be printed to stdout.


## tips & tricks

**voice expressiveness**

The instrument definition stored in an MDX file does not define many of the expressive features commonly used in a lovingly crafted DX synthesizer patch: vibrato, key velocity response and so on. MXDRV used effects in the note streams to apply such expression, rather than implementing them in the instruments.

Fear not! Restoring expressiveness is usually a simple matter of adding key velocity response (KVS) to the operators. Adding KVS to a carrier makes that operator chain respond to key velocity by adjusting the final output volume. Adding KVS to a modulator usually yields a more interesting result since you can then vary the modulation amount with the key velocity – essential for that FM slap bass!


---

Programmed by David Lindecrantz and distributed under the terms of the [MIT license](./LICENSE).

