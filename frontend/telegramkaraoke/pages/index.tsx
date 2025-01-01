import Head from "next/head";
import Image from "next/image";
import { Inter } from "next/font/google";
import { useState } from "react";
import styles from "@/styles/Home.module.css";
import Moment from "react-moment";
import {
  Address,
  ConnectButton,
  Connector,
  NFTCard,
  useNFT,
} from "@ant-design/web3";
import { getWeb3AssetUrl } from "@ant-design/web3-common";
import {
  MetaMask,
  OkxWallet,
  TokenPocket,
  WagmiWeb3ConfigProvider,
  WalletConnect,
  Sepolia,
} from "@ant-design/web3-wagmi";
import { abi } from "../contract";
import {
  WagmiProvider,
  http,
  createConfig,
  useAccount,
  useReadContract,
  useReadContracts,
} from "wagmi";
import { QueryClient } from "@tanstack/react-query";
import { injected, walletConnect } from "wagmi/connectors";

import { Button, Flex, Modal, Spin, Switch } from "antd";

const inter = Inter({ subsets: ["latin"] });

import { mainnet, sepolia, opBNBTestnet } from "wagmi/chains";

const config = createConfig({
  chains: [opBNBTestnet],
  transports: {
    [opBNBTestnet.id]: http(),
  },
  connectors: [
    walletConnect({
      projectId: "34da132a2121bd794c24d11fb06ef725",
      showQrModal: false,
    }),
  ],
});

const queryClient = new QueryClient();

const contractAddress = "0xCB7b3F767D536b7F884f0342372D8dE6E577a1e2";

export default function Home() {
  const [open, setOpen] = useState(false);
  const [filterOwned, setFilterOwned] = useState(false);

  const toggleFilter = () => {
    setFilterOwned(!filterOwned);
    console.log(filterOwned);
  };

  return (
    <>
      <Head>
        <title>Telegram Karaoke Bot</title>
        <meta name="description" content="Telegram Karaoke Bot NFTs" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main className={styles.main}>
        <WagmiWeb3ConfigProvider
          eip6963={{
            autoAddInjectedWallets: true,
          }}
          config={config}
          ens
          wallets={[
            MetaMask(),
            WalletConnect(),
            TokenPocket({
              group: "Popular",
            }),
            OkxWallet(),
          ]}
          balance
          queryClient={queryClient}
        >
          <Flex
            gap="middle"
            justify="space-between"
            align="center"
            className={styles.header}
          >
            <h1 className={styles.h1}>Telegram Karaoke</h1>

            <Flex gap="small" align="center">
              <FilterToggle toggleFilter={toggleFilter} filter={filterOwned} />

              <Connector
                modalProps={{
                  mode: "simple",
                }}
              >
                <ConnectButton size="large" quickConnect />
              </Connector>

              <Button type="primary" size="large" onClick={() => setOpen(true)}>
                Play on Telegram!
              </Button>
            </Flex>
            <Modal
              title="How to play"
              centered
              open={open}
              onOk={() => setOpen(false)}
              onCancel={() => setOpen(false)}
            >
              <h2>Start conversation with the bot:</h2>
              <img src="/qr.png"></img>
              <h2>Use the /help command to start!</h2>
            </Modal>
          </Flex>

          <Content filterOwned={filterOwned}></Content>

          <footer className={styles.footer}>
            Background Designed by <a href="www.freepik.com">Freepik</a>
          </footer>
        </WagmiWeb3ConfigProvider>
      </main>
    </>
  );
}

function Content({ filterOwned }: { filterOwned: boolean }) {
  const result = useReadContract({
    address: contractAddress,
    abi: abi,
    functionName: "tokenCount",
  });

  const contractCalls = Array.from({ length: Number(result.data) }).map(
    (_, index) => ({
      abi: abi,
      address: contractAddress,
      functionName: "ownerOf",
      args: [index + 1],
    }),
  );

  const { data: owners, isLoading: ownersLoading } = useReadContracts({
    contracts: contractCalls,
  } as {});

  const { address } = useAccount();

  if (result.isLoading || ownersLoading || owners === undefined) {
    return <Spin spinning fullscreen />;
  }

  if (result.error) {
    return <div>Error: {result.error.message}</div>;
  }

  const tokenCount = Number(result.data) - 1;

  return (
    <>
      <Flex wrap gap="middle" justify="space-evenly" align="center">
        {[...Array(tokenCount).keys()]
          .reverse()
          .filter((i) => {
            if (!filterOwned || address === undefined) return true;
            return owners[i].result === address;
          })
          .map((i) => (
            <NFTContent
              key={i}
              tokenId={i + 1}
              tokenOwner={owners[i]}
            ></NFTContent>
          ))}
      </Flex>
    </>
  );
}

function NFTContent({
  tokenId,
  tokenOwner,
}: {
  tokenId: number;
  tokenOwner: { result?: unknown; status: string };
}) {
  const { metadata, error, loading } = useNFT(contractAddress, tokenId);

  if (loading || metadata.attributes === undefined) return <></>;

  const ownerAddr = String(tokenOwner.result);

  const attributes = metadata.attributes || [];

  let score = 0;
  let song = "";
  let time = "";
  for (let attr of attributes) {
    if (attr.trait_type === "Score") {
      score = Number(attr.value);
    } else if (attr.trait_type === "Song") {
      song = attr.value || "";
    } else if (attr.trait_type === "Timestamp") {
      time = attr.value || "";
    } else if ("score" in attr) {
      score = Number(attr.score);
    } else if ("song" in attr) {
      song = (attr.song as string) || "";
    } else if ("timestamp" in attr) {
      time = attr.timestamp as string;
    }
  }

  const description = (
    <div>
      <p>Score: {score}</p>
      <p>Song: {song}</p>
      <p>
        Time: <Moment parse="YYYYMMDDhhmmss">{time}</Moment>
      </p>
      <p>Token ID: {tokenId}</p>
    </div>
  );

  return (
    <NFTCard
      address={contractAddress}
      tokenId={tokenId}
      description={description}
      footer=<>
        <div>Owner:</div>
        <Address address={ownerAddr} copyable></Address>
      </>
    />
  );
}

function FilterToggle({
  toggleFilter,
  filter,
}: {
  toggleFilter: (a: boolean) => void;
  filter: boolean;
}) {
  const { address } = useAccount();
  return (
    <>
      {address && (
        <Switch
          size="default"
          checkedChildren="Show All NFTs"
          unCheckedChildren="Show Owned NFTs"
          checked={!filter}
          onClick={toggleFilter}
        />
      )}
    </>
  );
}
