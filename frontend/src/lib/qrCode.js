const RS_BLOCKS_LOW = {
  1: [[1, 26, 19]],
  2: [[1, 44, 34]],
  3: [[1, 70, 55]],
  4: [[1, 100, 80]],
  5: [[1, 134, 108]],
  6: [[2, 86, 68]],
  7: [[2, 98, 78]],
  8: [[2, 121, 97]],
  9: [[2, 146, 116]],
  10: [[2, 86, 68], [2, 87, 69]],
}

const ALIGNMENT_POSITIONS = {
  1: [],
  2: [6, 18],
  3: [6, 22],
  4: [6, 26],
  5: [6, 30],
  6: [6, 34],
  7: [6, 22, 38],
  8: [6, 24, 42],
  9: [6, 26, 46],
  10: [6, 28, 50],
}

function appendBits(buffer, value, length) {
  for (let i = length - 1; i >= 0; i -= 1) {
    buffer.push((value >>> i) & 1)
  }
}

function bitsToBytes(bits) {
  const bytes = []
  for (let i = 0; i < bits.length; i += 8) {
    let value = 0
    for (let j = 0; j < 8; j += 1) {
      value = (value << 1) | (bits[i + j] || 0)
    }
    bytes.push(value)
  }
  return bytes
}

function createGfTables() {
  const exp = new Array(512)
  const log = new Array(256)
  let value = 1

  for (let i = 0; i < 255; i += 1) {
    exp[i] = value
    log[value] = i
    value <<= 1
    if (value & 0x100) value ^= 0x11d
  }

  for (let i = 255; i < 512; i += 1) {
    exp[i] = exp[i - 255]
  }

  return { exp, log }
}

const GF = createGfTables()

function gfMultiply(left, right) {
  if (!left || !right) return 0
  return GF.exp[GF.log[left] + GF.log[right]]
}

function reedSolomonGenerator(degree) {
  let result = [1]

  for (let i = 0; i < degree; i += 1) {
    const next = new Array(result.length + 1).fill(0)
    for (let j = 0; j < result.length; j += 1) {
      next[j] ^= result[j]
      next[j + 1] ^= gfMultiply(result[j], GF.exp[i])
    }
    result = next
  }

  return result
}

function reedSolomonRemainder(data, degree) {
  const generator = reedSolomonGenerator(degree)
  const result = new Array(degree).fill(0)

  for (const byte of data) {
    const factor = byte ^ result.shift()
    result.push(0)

    for (let i = 0; i < degree; i += 1) {
      result[i] ^= gfMultiply(generator[i + 1], factor)
    }
  }

  return result
}

function blocksForVersion(version) {
  return RS_BLOCKS_LOW[version].flatMap(([count, totalCount, dataCount]) => {
    return Array.from({ length: count }, () => ({ totalCount, dataCount }))
  })
}

function dataCapacity(version) {
  return blocksForVersion(version).reduce((sum, block) => sum + block.dataCount, 0)
}

function chooseVersion(byteLength) {
  for (let version = 1; version <= 10; version += 1) {
    const lengthBits = version < 10 ? 8 : 16
    const requiredBits = 4 + lengthBits + (byteLength * 8)
    if (requiredBits <= dataCapacity(version) * 8) return version
  }
  return null
}

function encodeData(value, version) {
  const data = Array.from(new TextEncoder().encode(value))
  const capacity = dataCapacity(version)
  const bits = []

  appendBits(bits, 0x4, 4)
  appendBits(bits, data.length, version < 10 ? 8 : 16)
  for (const byte of data) appendBits(bits, byte, 8)

  const capacityBits = capacity * 8
  appendBits(bits, 0, Math.min(4, capacityBits - bits.length))
  while (bits.length % 8) bits.push(0)

  const bytes = bitsToBytes(bits)
  const padBytes = [0xec, 0x11]
  for (let i = 0; bytes.length < capacity; i += 1) {
    bytes.push(padBytes[i % 2])
  }

  const blocks = []
  let offset = 0
  for (const block of blocksForVersion(version)) {
    const dataCodewords = bytes.slice(offset, offset + block.dataCount)
    const eccCodewords = reedSolomonRemainder(dataCodewords, block.totalCount - block.dataCount)
    blocks.push({ dataCodewords, eccCodewords })
    offset += block.dataCount
  }

  const result = []
  const maxData = Math.max(...blocks.map((block) => block.dataCodewords.length))
  const maxEcc = Math.max(...blocks.map((block) => block.eccCodewords.length))

  for (let i = 0; i < maxData; i += 1) {
    for (const block of blocks) {
      if (i < block.dataCodewords.length) result.push(block.dataCodewords[i])
    }
  }

  for (let i = 0; i < maxEcc; i += 1) {
    for (const block of blocks) {
      if (i < block.eccCodewords.length) result.push(block.eccCodewords[i])
    }
  }

  return result.flatMap((byte) => {
    const byteBits = []
    appendBits(byteBits, byte, 8)
    return byteBits
  })
}

function createMatrix(size) {
  return {
    modules: Array.from({ length: size }, () => Array(size).fill(false)),
    reserved: Array.from({ length: size }, () => Array(size).fill(false)),
  }
}

function setModule(matrix, x, y, value, reserved = true) {
  if (x < 0 || y < 0 || y >= matrix.modules.length || x >= matrix.modules.length) return
  matrix.modules[y][x] = Boolean(value)
  if (reserved) matrix.reserved[y][x] = true
}

function drawFinder(matrix, x, y) {
  for (let dy = -1; dy <= 7; dy += 1) {
    for (let dx = -1; dx <= 7; dx += 1) {
      const xx = x + dx
      const yy = y + dy
      const isFinder = dx >= 0 && dx <= 6 && dy >= 0 && dy <= 6
      const isDark = isFinder && (dx === 0 || dx === 6 || dy === 0 || dy === 6 || (dx >= 2 && dx <= 4 && dy >= 2 && dy <= 4))
      setModule(matrix, xx, yy, isDark)
    }
  }
}

function drawAlignment(matrix, centerX, centerY) {
  if (matrix.reserved[centerY]?.[centerX]) return

  for (let dy = -2; dy <= 2; dy += 1) {
    for (let dx = -2; dx <= 2; dx += 1) {
      const distance = Math.max(Math.abs(dx), Math.abs(dy))
      setModule(matrix, centerX + dx, centerY + dy, distance !== 1)
    }
  }
}

function versionBits(version) {
  let bits = version << 12
  const generator = 0x1f25

  for (let i = 17; i >= 12; i -= 1) {
    if ((bits >>> i) & 1) bits ^= generator << (i - 12)
  }

  return ((version << 12) | bits) & 0x3ffff
}

function drawVersionBits(matrix, version) {
  if (version < 7) return

  const size = matrix.modules.length
  const bits = versionBits(version)

  for (let i = 0; i < 18; i += 1) {
    const dark = ((bits >>> i) & 1) !== 0
    const x = size - 11 + (i % 3)
    const y = Math.floor(i / 3)
    setModule(matrix, x, y, dark)
    setModule(matrix, y, x, dark)
  }
}

function drawFunctionPatterns(matrix, version) {
  const size = matrix.modules.length
  drawFinder(matrix, 0, 0)
  drawFinder(matrix, size - 7, 0)
  drawFinder(matrix, 0, size - 7)

  for (let i = 8; i < size - 8; i += 1) {
    const dark = i % 2 === 0
    setModule(matrix, 6, i, dark)
    setModule(matrix, i, 6, dark)
  }

  const positions = ALIGNMENT_POSITIONS[version]
  for (const y of positions) {
    for (const x of positions) {
      drawAlignment(matrix, x, y)
    }
  }

  setModule(matrix, 8, size - 8, true)

  for (let i = 0; i < 9; i += 1) {
    setModule(matrix, 8, i, false)
    setModule(matrix, i, 8, false)
  }
  for (let i = size - 8; i < size; i += 1) {
    setModule(matrix, 8, i, false)
    setModule(matrix, i, 8, false)
  }

  drawVersionBits(matrix, version)
}

function placeData(matrix, bits) {
  const size = matrix.modules.length
  let bitIndex = 0
  let upwards = true

  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right -= 1

    for (let vertical = 0; vertical < size; vertical += 1) {
      const y = upwards ? size - 1 - vertical : vertical
      for (let dx = 0; dx < 2; dx += 1) {
        const x = right - dx
        if (matrix.reserved[y][x]) continue
        setModule(matrix, x, y, bits[bitIndex] || 0, false)
        bitIndex += 1
      }
    }

    upwards = !upwards
  }
}

function maskBit(mask, x, y) {
  switch (mask) {
    case 0: return (x + y) % 2 === 0
    case 1: return y % 2 === 0
    case 2: return x % 3 === 0
    case 3: return (x + y) % 3 === 0
    case 4: return (Math.floor(y / 2) + Math.floor(x / 3)) % 2 === 0
    case 5: return ((x * y) % 2) + ((x * y) % 3) === 0
    case 6: return (((x * y) % 2) + ((x * y) % 3)) % 2 === 0
    case 7: return (((x + y) % 2) + ((x * y) % 3)) % 2 === 0
    default: return false
  }
}

function applyMask(base, mask) {
  const size = base.modules.length
  const matrix = {
    modules: base.modules.map((row) => [...row]),
    reserved: base.reserved.map((row) => [...row]),
  }

  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      if (!matrix.reserved[y][x] && maskBit(mask, x, y)) {
        matrix.modules[y][x] = !matrix.modules[y][x]
      }
    }
  }

  return matrix
}

function penalty(matrix) {
  const size = matrix.modules.length
  let score = 0

  for (let y = 0; y < size; y += 1) {
    let runColor = matrix.modules[y][0]
    let runLength = 1
    for (let x = 1; x < size; x += 1) {
      if (matrix.modules[y][x] === runColor) {
        runLength += 1
      } else {
        if (runLength >= 5) score += 3 + runLength - 5
        runColor = matrix.modules[y][x]
        runLength = 1
      }
    }
    if (runLength >= 5) score += 3 + runLength - 5
  }

  for (let x = 0; x < size; x += 1) {
    let runColor = matrix.modules[0][x]
    let runLength = 1
    for (let y = 1; y < size; y += 1) {
      if (matrix.modules[y][x] === runColor) {
        runLength += 1
      } else {
        if (runLength >= 5) score += 3 + runLength - 5
        runColor = matrix.modules[y][x]
        runLength = 1
      }
    }
    if (runLength >= 5) score += 3 + runLength - 5
  }

  for (let y = 0; y < size - 1; y += 1) {
    for (let x = 0; x < size - 1; x += 1) {
      const color = matrix.modules[y][x]
      if (color === matrix.modules[y][x + 1] && color === matrix.modules[y + 1][x] && color === matrix.modules[y + 1][x + 1]) {
        score += 3
      }
    }
  }

  let dark = 0
  for (const row of matrix.modules) {
    for (const cell of row) {
      if (cell) dark += 1
    }
  }
  score += Math.floor(Math.abs((dark * 20 / (size * size)) - 10)) * 10

  return score
}

function formatBits(mask) {
  const data = (1 << 3) | mask
  let bits = data << 10
  const generator = 0x537

  for (let i = 14; i >= 10; i -= 1) {
    if ((bits >>> i) & 1) bits ^= generator << (i - 10)
  }

  return (((data << 10) | bits) ^ 0x5412) & 0x7fff
}

function drawFormatBits(matrix, mask) {
  const size = matrix.modules.length
  const bits = formatBits(mask)

  for (let i = 0; i <= 5; i += 1) setModule(matrix, 8, i, ((bits >>> i) & 1) !== 0)
  setModule(matrix, 8, 7, ((bits >>> 6) & 1) !== 0)
  setModule(matrix, 8, 8, ((bits >>> 7) & 1) !== 0)
  setModule(matrix, 7, 8, ((bits >>> 8) & 1) !== 0)
  for (let i = 9; i < 15; i += 1) setModule(matrix, 14 - i, 8, ((bits >>> i) & 1) !== 0)

  for (let i = 0; i < 8; i += 1) setModule(matrix, size - 1 - i, 8, ((bits >>> i) & 1) !== 0)
  for (let i = 8; i < 15; i += 1) setModule(matrix, 8, size - 15 + i, ((bits >>> i) & 1) !== 0)
  setModule(matrix, 8, size - 8, true)
}

export function createQrMatrix(value) {
  if (!value) return null

  const byteLength = new TextEncoder().encode(value).length
  const version = chooseVersion(byteLength)
  if (!version) return null

  const size = 21 + (version - 1) * 4
  const base = createMatrix(size)
  drawFunctionPatterns(base, version)
  placeData(base, encodeData(value, version))

  let bestMask = 0
  let bestMatrix = null
  let bestPenalty = Infinity

  for (let mask = 0; mask < 8; mask += 1) {
    const candidate = applyMask(base, mask)
    drawFormatBits(candidate, mask)
    const candidatePenalty = penalty(candidate)
    if (candidatePenalty < bestPenalty) {
      bestPenalty = candidatePenalty
      bestMask = mask
      bestMatrix = candidate
    }
  }

  drawFormatBits(bestMatrix, bestMask)
  return bestMatrix.modules
}
