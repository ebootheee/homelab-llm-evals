**Question 1:**
The solar flux on a horizontal surface is given by $I = I_0 \sin(\theta)$, where $\theta$ is the solar altitude angle. At solar noon, the altitude angle is given by $\theta = 90^\circ - |latitude - declination|$. For Miami ($26^\circ$ N) on the winter solstice, the sun's declination is approximately $-23.5^\circ$.
$\theta = 90^\circ - |26^\circ - (-23.5^\circ)| = 90^\circ - 49.5^\circ = 40.5^\circ$.
The fraction of flux is $\sin(40.5^\circ) \approx 0.649$. Considering atmospheric absorption (often modeled to reduce the effective constant or included in "standard" values in such problems), or simply checking the closest option, 0.656 is the best fit. Let's re-evaluate with declination $-23.44^\circ$. $\theta = 90 - (26+23.44) = 40.56^\circ$. $\sin(40.56^\circ) \approx 0.650$. Option D is 0.656, which is very close. Other options are further away.

ANSWER 1: D

**Question 2:**
In interferometry, a shift of one full fringe corresponds to a path difference change of $\lambda$. Since the light travels down and up (reflection), a surface height change $h$ causes a path difference of $2h$. Thus, one fringe shift corresponds to a height change of $\lambda/2$.
Given a distortion of 0.4 fringes, the depth/elevation $d$ is:
$d = 0.4 \times \frac{\lambda}{2} = 0.2 \lambda$.
With $\lambda = 535 \text{ nm} = 535 \times 10^{-9} \text{ m}$,
$d = 0.2 \times 535 \times 10^{-9} \text{ m}$.
This matches option B.

ANSWER 2: B

**Question 3:**
Illuminance $E$ is given by the inverse square law: $E = I / r^2$.
The problem states the illuminance from the standard lamp equals that from the unknown lamp.
$I_1 / r_1^2 = I_2 / r_2^2$.
Given $I_1 = 48$ candles, $r_1 = 36$ in, $r_2 = 45$ in.
$48 / 36^2 = I_2 / 45^2$.
$I_2 = 48 \times (45/36)^2 = 48 \times (1.25)^2 = 48 \times 1.5625 = 75$ candles.

ANSWER 3: G

**Question 4:**
The potential energy $U(R_e)$ at the equilibrium bond length is related to the dissociation energy $D_e$ by considering the zero of potential energy at infinite separation. Usually, $D_e$ is defined as the depth of the potential well from the minimum to the asymptotic limit (0 eV). Therefore, the potential energy at the minimum is $U(R_e) = -D_e$.
However, sometimes $D_0$ (from zero-point energy) is given. Here it says $D_e$, which typically refers to the dissociation energy from the bottom of the well ($v=0$ level included in the definition of the curve's minimum relative to asymptote).
Wait, standard notation: $D_e$ is the depth of the potential well (from minimum to 0). So $U(R_e) = -D_e = -4.75$ eV? No, that's too small for H2. The total electronic energy is around -16 eV relative to separated atoms. But usually, "potential energy" in this context might refer to the total energy or the Morse potential value.
Let's look at the options: ~-30 eV. This suggests the question asks for the total electronic energy or the value relative to separated nuclei and electrons?
Actually, for H2, the binding energy is ~4.5 eV. The ionization energy of H2 is ~15.4 eV. The second ionization is ~31 eV? No.
Let's re-read carefully. $D_e = 4.75$ eV. This is the dissociation energy. The potential energy well depth is 4.75 eV. If the zero of potential energy is at separated *atoms*, then $U(R_e) = -4.75$ eV. None of the options match.
If the zero is at separated *nuclei* and *electrons* (total energy), we need more data.
However, often in spectroscopy contexts, $D_e$ is just the well depth. Is it possible the question implies the Morse potential parameter?
Let's check the magnitude. H2 total energy at equilibrium is roughly -31.7 eV (relative to 2 protons + 2 electrons). The options are around -30 to -35 eV. This confirms $U(R_e)$ refers to the total electronic energy.
Without explicit formulae, we rely on known values. The ground state energy of H2 is approximately -31.7 eV (or -184 eV in atomic units? No, 1 Hartree = 27.2 eV. $E \approx -1.16$ Ha $\approx -31.6$ eV).
Option B (-30.77) and F (-31.95) are close.
Let's calculate using the Morse potential if parameters were given? Only $D_e$ and $R_e$ are given. This is insufficient to determine the total energy unless we assume a specific model or standard value.
However, looking at similar textbook problems, the "potential energy" often cited for H2 in this context (total electronic energy) is approx -31.7 eV.
Let's look at Option B: -30.77 eV. Option F: -31.95 eV.
Standard value: The ground state energy of H2 is -16.84 eV relative to separated atoms? No, that's not right.
Ionization energy 1st: 15.4 eV. 2nd: 31.0 eV (approx, for H+). Total to 2H+ + 2e- is ~46 eV?
Let's use the known total energy of H2 ground state: $E_{total} \approx -31.7$ eV.
Between B and F, F (-31.95) is closer to -31.7 than B (-30.77).
Wait, let's check Option D: -28.57.
Let's reconsider the definition. If $U(R_e)$ is just the potential part of the Hamiltonian (Coulomb), it includes electron-nucleus, nucleus-nucleus, and electron-electron terms.
At $R=0.741$ A, the Coulomb energy is indeed around -31 to -32 eV.
Let's guess F based on standard literature values for H2 electronic energy.

ANSWER 4: F

**Question 5:**
The standard cell potential $E^\circ$ is related to the standard Gibbs free energy change $\Delta G^\circ$ by the equation:
$\Delta G^\circ = -n F E^\circ$
For the reaction $2\text{H}_2 + \text{O}_2 \rightarrow 2\text{H}_2\text{O}$, $n = 4$ electrons are transferred per 2 moles of water, or $n=2$ for 1 mole of water.
The given $\Delta G^\circ_f$ is for 1 mole of $\text{H}_2\text{O}(l)$, which is $-56,690$ cal/mol.
So, for the formation of 1 mole of water:
$\Delta G^\circ = -56,690$ cal/mol.
Number of electrons exchanged to form 1 mole of water from H2 and O2:
$\text{H}_2 \rightarrow 2\text{H}^+ + 2e^-$
$\frac{1}{2}\text{O}_2 + 2e^- \rightarrow \text{O}^{2-}$ (conceptually)
Overall: $\text{H}_2 + \frac{1}{2}\text{O}_2 \rightarrow \text{H}_2\text{O}$. Here $n=2$.
$E^\circ = -\Delta G^\circ / (n F)$
Convert $\Delta G^\circ$ to Joules: $-56,690 \text{ cal/mol} \times 4.184 \text{ J/cal} \approx -237,190 \text{ J/mol}$.
$F \approx 96,485 \text{ C/mol}$.
$n = 2$.
$E^\circ = -(-237,190) / (2 \times 96,485) = 237,190 / 192,970 \approx 1.229$ V.

ANSWER 5: F

**Question 6:**
Kepler's Third Law states that $T^2 \propto r^3$, or $\frac{T_2^2}{T_1^2} = \frac{r_2^3}{r_1^3}$.
Thus, $T_2 = T_1 \sqrt{\left(\frac{r_2}{r_1}\right)^3} = T_1 \left(\frac{r_2}{r_1}\right)^{3/2}$.
Given:
$T_1 = 15.95$ days
$r_1 = 1.22 \times 10^9$ m
$r_2 = 1.48 \times 10^9$ m
Ratio $r_2/r_1 = 1.48 / 1.22 \approx 1.2131$.
$(r_2/r_1)^{3/2} = (1.2131)^{1.5} \approx 1.337$.
$T_2 = 15.95 \times 1.337 \approx 21.32$ days.
This matches Option B.

ANSWER 6: B

**Question 7:**
The cell is $\text{Ag}/\text{AgCl}/\text{Cl}^-$ (anode, oxidation) and $\text{Ce}^{4+}/\text{Ce}^{3+}$ (cathode, reduction).
Wait, the notation is $\text{Ag}/\text{AgCl}/\text{Cl}^-$ on the left (anode) and $\text{Ce}^{4+}, \text{Ce}^{3+}/\text{Pt}$ on the right (cathode).
$E_{cell} = E_{cathode} - E_{anode}$.

Cathode: $\text{Ce}^{4+} + e^- \rightarrow \text{Ce}^{3+}$
$E_{red} = E^\circ_{\text{Ce}} + \frac{0.0591}{1} \log \left( \frac{a_{\text{Ce}^{4+}}}{a_{\text{Ce}^{3+}}} \right)$ at 298 K.
$E^\circ_{\text{Ce}} = 1.45$ V.
$a_{\text{Ce}^{4+}} = 0.01$, $a_{\text{Ce}^{3+}} = 0.1$.
$E_{cathode} = 1.45 + 0.0591 \log(0.01/0.1) = 1.45 + 0.0591 \log(0.1) = 1.45 - 0.0591 = 1.3909$ V.

Anode: $\text{AgCl} + e^- \rightarrow \text{Ag} + \text{Cl}^-$ (Reduction potential given is for this half-reaction).
$E_{red} = E^\circ_{\text{AgCl}} - \frac{0.0591}{1} \log(a_{\text{Cl}^-})$.
$E^\circ_{\text{AgCl}} = 0.2225$ V.
$a_{\text{Cl}^-} = 0.0001 = 10^{-4}$.
$E_{anode (red)} = 0.2225 - 0.0591 \log(10^{-4}) = 0.2225 - 0.0591(-4) = 0.2225 + 0.2364 = 0.4589$ V.

Since the Ag/AgCl electrode is on the left, it acts as the anode (oxidation). The cell potential is calculated using reduction potentials:
$E_{cell} = E_{red, cathode} - E_{red, anode}$
$E_{cell} = 1.3909 \text{ V} - 0.4589 \text{ V} = 0.932$ V.
This is very close to Option D (0.9342 V). The slight difference might be due to using $R T / F \ln(10) \approx 0.05916$.
Using 0.05916:
$E_{cat} = 1.45 - 0.05916 = 1.39084$
$E_{an} = 0.2225 + 4(0.05916) = 0.2225 + 0.23664 = 0.45914$
$E_{cell} = 1.39084 - 0.45914 = 0.9317$ V.
Still closest to D.

ANSWER 7: D

**Question 8:**
The entropy change of the surroundings for a phase change at constant temperature and pressure is given by $\Delta S_{surr} = -\Delta H_{sys} / T$.
Here, the system is chloroform vaporizing.
$\Delta H_{vap} = 29.4 \text{ kJ/mol} = 29,400 \text{ J/mol}$.
$T = 334.88 \text{ K}$ (normal boiling point).
$\Delta S_{surr} = -29,400 \text{ J/mol} / 334.88 \text{ K}$.
Calculation: $29,400 / 334.88 \approx 87.79$ J/K mol.
So, $\Delta S_{surr} = -87.8$ J K$^{-1}$ mol$^{-1}$.
This matches Option C.

ANSWER 8: C

**Question 9:**
The photoelectric equation is $E_{photon} = \Phi + KE_{max}$, where $\Phi$ is the ionization energy (work function).
$E_{photon} = hc / \lambda$.
$\lambda = 58.4 \text{ nm} = 58.4 \times 10^{-9} \text{ m}$.
$h c \approx 1240 \text{ eV nm}$.
$E_{photon} = 1240 / 58.4 \approx 21.23$ eV.

Kinetic Energy of ejected electron:
$KE = \frac{1}{2} m v^2$.
$m_e \approx 9.109 \times 10^{-31}$ kg.
$v = 1.59 \times 10^6$ m/s.
$KE = 0.5 \times 9.109 \times 10^{-31} \times (1.59 \times 10^6)^2$ J.
$KE = 0.5 \times 9.109 \times 10^{-31} \times 2.528 \times 10^{12}$ J.
$KE \approx 11.47 \times 10^{-19}$ J.
Convert to eV: $1 \text{ eV} = 1.602 \times 10^{-19}$ J.
$KE_{eV} = 11.47 / 1.602 \approx 7.16$ eV.

Ionization Energy $\Phi = E_{photon} - KE$.
$\Phi = 21.23 \text{ eV} - 7.16 \text{ eV} = 14.07$ eV.
This is closest to Option C (14 eV).

ANSWER 9: C

**Question 10:**
We have two charges on the x-axis:
$q_1 = +2.1 \times 10^{-8}$ C at $x_1 = 20$ cm.
$q_2 = -4 q_1 = -8.4 \times 10^{-8}$ C at $x_2 = 70$ cm.
We need to find $x$ where $E_{net} = 0$.
Since the charges have opposite signs, the zero-field point must lie outside the region between them (where fields add up). It must be closer to the smaller magnitude charge ($q_1$) because the field from $q_2$ is stronger due to larger charge, so we need to be closer to $q_1$ to compensate for distance? No, $E = kQ/r^2$. To balance a larger Q, you need a larger r. So the point is farther from the larger charge ($q_2$) and closer to the smaller charge ($q_1$).
Since $|q_2| > |q_1|$, the null point is on the side of $q_1$.
So $x < 20$ cm.
Let the position be $x$. Distance to $q_1$ is $|x - 20|$. Distance to $q_2$ is $|x - 70|$.
Since $x < 20$, distance to $q_1$ is $20 - x$. Distance to $q_2$ is $70 - x$.
Equating magnitudes:
$\frac{k |q_1|}{(20 - x)^2} = \frac{k |q_2|}{(70 - x)^2}$
$\frac{q_1}{(20 - x)^2} = \frac{4 q_1}{(70 - x)^2}$
$\frac{1}{(20 - x)^2} = \frac{4}{(70 - x)^2}$
Taking the square root:
$\frac{1}{20 - x} = \frac{2}{70 - x}$ (Note: distances are positive, so we take positive roots)
$70 - x = 2(20 - x)$
$70 - x = 40 - 2x$
$x = 40 - 70 = -30$ cm.

Check:
At $x = -30$:
Dist to $q_1$ (at 20) is 50 cm. $E_1 \propto 1/50^2$. Direction: Away from $q_1$ (left, negative x).
Dist to $q_2$ (at 70) is 100 cm. $E_2 \propto 4/100^2 = 4/10000 = 1/2500$.
$E_1 \propto 1/2500 = 1/2500$. Direction: Towards $q_2$ (right, positive x)? No, $q_2$ is negative, so field points towards $q_2$ (right).
Wait.
$q_1$ is positive. Field at $x=-30$ points LEFT (away from 20).
$q_2$ is negative. Field at $x=-30$ points RIGHT (towards 70).
Magnitudes are equal ($1/2500$ vs $4/10000 = 1/2500$).
Vectors oppose. Net field is zero.

ANSWER 10: C

```text
ANSWER 1: D
ANSWER 2: B
ANSWER 3: G
ANSWER 4: F
ANSWER 5: F
ANSWER 6: B
ANSWER 7: D
ANSWER 8: C
ANSWER 9: C
ANSWER 10: C
```