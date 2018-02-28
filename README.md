# MDXtract
MDXtract is a set of python utilities for extracting instrument and sample data from MDX/PDX files. MDX is a binary [MML](https://en.wikipedia.org/wiki/Music_Macro_Language) representation used by [MXDRV](https://www16.atwiki.jp/mxdrv/pages/23.html), a popular sound driver for the Sharp [X68000](https://en.wikipedia.org/wiki/X68000) computer. 

Instrument definitions for the amazing [YM2151](https://en.wikipedia.org/wiki/Yamaha_YM2151) (OPM) FM tone generator are embedded in these files. MXDRV can also utilize the super crunchy OKI MSM6258V for ADPCM samples, which are stored in a supplementary PDX file.

mdxtract.py extracts YM2151 instruments from MDX files and converts them to [DX7](https://en.wikipedia.org/wiki/Yamaha_DX7) compatible [sysex](http://electronicmusic.wikia.com/wiki/System_exclusive) data. The data can be imported into many [popular](https://asb2m10.github.io/dexed/) [software](https://www.arturia.com/dx7-v/overview) [FM](https://www.native-instruments.com/en/products/komplete/synths/fm8/) synthesizers, as well as the original hardware.

pdxtract.py extracts 4-bit ADPCM samples from PDX files and converts them to standard 16-bit WAV files.


## operation

**mdxtract.py**
```
mdxtract.py [-h, --help] [-v, --verbose] [infiles ...]
```
 - Instrument data will be converted and written as `<filename>.syx`
 - In verbose mode some intriguing data will be printed to stdout

**pdxtract.py**
```
pdxtract.py [-h, --help] [infiles ...]
```
 - ADPCM data will be converted and written as `<filename>_<n>.wav`


## tips & tricks

**voice expressiveness**

The instrument definition stored in an MDX file does not define many of the expressive features commonly used in a lovingly crafted DX synthesizer patch: vibrato, key velocity response and so on. MXDRV used effects in the note streams to apply such expression, rather than implementing them in the instruments.

Fear not! Restoring expressiveness is usually a simple matter of adding key velocity response (KVS) to the operators. Adding KVS to a carrier makes that operator chain respond to key velocity by adjusting the final output volume. Adding KVS to a modulator usually yields a more interesting result since you can then vary the modulation amount with the key velocity – essential for that FM slap bass!


---

Developed by David Lindecrantz and distributed under the terms of the [MIT license](./LICENSE).

